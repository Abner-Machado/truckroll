#!/usr/bin/env python3
"""truckroll jury - measure whether the sheet changes a diagnosis, instead of claiming it does.

Three things happen here, and none of them touch the network:

    packs     build the blind prompt packs, one per case per arm
    score     read the judges' answers back and write SCORES.md
    selftest  prove the scorer works, against answers whose verdict is known

An arm is what the judge was given: the sheet, a generic list, or nothing at all.
A knockout drops one rule from the sheet and asks the same questions again. A rule whose
removal changes no answer is a rule carrying less weight than its confidence claims.

Python standard library only. No install, no network, no key.

    python jury.py packs
    python jury.py packs --knockout 7
    python jury.py score
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

__version__ = "0.1.0"

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = ("sheet", "generic", "none")

RULE_LINE = re.compile(r"^(\d+)\.\s+`(?P<scope>[^`]+)`\s+(?P<text>.*)$")

ASK = """You are diagnosing a field failure in an embedded device.

INCIDENT REPORT
{report}

QUESTION
Name the single engineering decision that would most likely have prevented this, in one
sentence. Then, in a second sentence, say how it would have prevented it.

{context}
Answer in English. Do not restate the report."""

CONTEXT = {
    "sheet": "Use the decision sheet below, and end your answer with the number of the rule you"
             " used, written as RULE: n.\n\n{body}\n",
    "generic": "Use the checklist below.\n\n{body}\n",
    "none": "Answer from your own engineering judgement. No checklist is provided.\n",
}

FORCED = """Three checklists are given below, labelled S1, S2 and S3. One of them may be empty.

INCIDENT REPORT
{report}

For each checklist, decide whether it contains an item that would have prevented this
failure. Then answer with a single line, `BEST: Sn`, naming the checklist that most
directly prevents it, or `BEST: none` if none does. Add one sentence saying why.

{bodies}"""


# ----------------------------------------------------------------- loading

def load_cases():
    with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as fh:
        return json.load(fh)["cases"]


def load_rules(path="TASTE.md"):
    """Every numbered rule in the sheet, as {number: full line}."""
    rules = {}
    with open(os.path.join(HERE, path), encoding="utf-8") as fh:
        for line in fh:
            m = RULE_LINE.match(line.strip())
            if m:
                rules[int(m.group(1))] = line.strip()
    return rules


def sheet_body(drop=None):
    rules = load_rules()
    if drop is not None:
        if drop not in rules:
            sys.exit(f"jury: there is no rule {drop} in TASTE.md")
        del rules[drop]
    return "\n".join(rules[n] for n in sorted(rules))


def generic_body():
    with open(os.path.join(HERE, "generic.md"), encoding="utf-8") as fh:
        return fh.read().strip()


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ----------------------------------------------------------------- packs

def write_pack(subdir, case_id, text, manifest):
    out = os.path.join(HERE, "packs", subdir)
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, f"{case_id}.txt")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    manifest[f"{subdir}/{case_id}.txt"] = digest(text)


def cmd_packs(args):
    cases = load_cases()
    manifest = {}
    bodies = {"sheet": sheet_body(args.knockout), "generic": generic_body(), "none": ""}
    tag = "" if args.knockout is None else f"knockout-{args.knockout}-"

    field = "report_easy" if args.easy else "report_hard"
    for case in cases:
        for arm in ARMS:
            ctx = CONTEXT[arm].format(body=bodies[arm]) if bodies[arm] else CONTEXT[arm]
            text = ASK.format(report=case[field], context=ctx)
            write_pack(tag + arm, case["id"], text, manifest)

    # Forced choice: the three arms side by side under neutral labels. The order is a
    # balanced rotation, not a shuffle. A shuffle over eight cases left the sheet in the
    # last slot five times out of eight, and position bias in a model acting as judge is
    # real enough to swamp the effect being measured. Rotation gives each arm each slot
    # within one of even, and needs no seed to reproduce.
    order_map = {}
    for i, case in enumerate(cases):
        base = ["sheet", "generic", "none"]
        labels = base[i % 3:] + base[:i % 3]
        order_map[case["id"]] = {f"S{j + 1}": labels[j] for j in range(3)}
        blocks = []
        for i, arm in enumerate(labels, start=1):
            body = bodies[arm] or "(empty)"
            blocks.append(f"=== S{i} ===\n{body}\n")
        text = FORCED.format(report=case[field], bodies="\n".join(blocks))
        write_pack(tag + "forced", case["id"], text, manifest)

    meta = {
        "version": __version__,
        "label_order": "balanced rotation by case index",
        "report": field,
        "knockout": args.knockout,
        "sheet_digest": digest(bodies["sheet"]),
        "forced_label_map": order_map,
        "pack_digests": manifest,
    }
    with open(os.path.join(HERE, "packs", f"{tag or ''}manifest.json"), "w",
              encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print(f"{len(manifest)} packs written to packs/ ({len(cases)} cases x 4)")
    print(f"sheet digest {meta['sheet_digest']}  knockout {args.knockout}")
    print("Answers go in judges/<model>/<arm>/<case>.txt, then: python jury.py score")
    return 0


# ----------------------------------------------------------------- scoring

def normalise(text):
    return re.sub(r"\s+", " ", text.lower())


def hit(answer, key):
    """A hit needs every all_of group and every any_of group satisfied.

    A group is satisfied when at least one of its phrases appears. The groups are in
    cases.json in the open: disagree with one and the verdict is auditable, which is the
    only reason a keyed scorer is worth more than asking a model to grade itself.
    """
    text = normalise(answer)
    groups = list(key.get("all_of", [])) + list(key.get("any_of", []))
    missed = [g for g in groups if not any(normalise(p) in text for p in g)]
    return (not missed), missed


def claimed_rule(answer):
    m = re.search(r"rule:\s*(\d+)", answer, re.IGNORECASE)
    return int(m.group(1)) if m else None


def list_judges(root="judges"):
    """Every judge directory, so one that answered nothing still shows up as nothing."""
    base = os.path.join(HERE, root)
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base)
                  if os.path.isdir(os.path.join(base, d)) and not d.startswith("_"))


def read_answers(root="judges"):
    """judges/<model>/<arm>/<case>.txt -> {(model, arm, case): text}

    An empty file is not an answer. The bridge writes nothing when a model fails, and a
    judge that produced nothing has to appear as nothing rather than disappear.
    """
    found = {}
    base = os.path.join(HERE, root)
    if not os.path.isdir(base):
        return found
    for model in sorted(os.listdir(base)):
        mdir = os.path.join(base, model)
        if not os.path.isdir(mdir):
            continue
        for arm in sorted(os.listdir(mdir)):
            adir = os.path.join(mdir, arm)
            if not os.path.isdir(adir):
                continue
            for name in sorted(os.listdir(adir)):
                if not name.endswith(".txt"):
                    continue
                with open(os.path.join(adir, name), encoding="utf-8", errors="replace") as fh:
                    found[(model, arm, os.path.splitext(name)[0])] = fh.read()
    return found


def forced_pick(answer, label_map):
    m = re.search(r"best:\s*(s[123]|none)", answer, re.IGNORECASE)
    if not m:
        return None
    pick = m.group(1).upper()
    return "none-of-them" if pick == "NONE" else label_map.get(pick)


def cmd_score(args):
    cases = {c["id"]: c for c in load_cases()}
    answers = read_answers(args.root)
    if not answers:
        sys.exit("jury: judges/ is empty. Run the packs through a model first.")

    # The forced-choice labels mean nothing without the map that produced them, and
    # `packs` overwrites packs/manifest.json on every run. So the map has to travel with
    # the answers, as _manifest.json inside the answer tree. One round was lost to exactly
    # this: labels decoded against a later map, giving noise that looked like data.
    label_maps, map_source = {}, None
    for candidate, why in ((os.path.join(HERE, args.root, "_manifest.json"), "answer tree"),
                           (os.path.join(HERE, "packs", "manifest.json"), "packs")):
        if os.path.exists(candidate):
            with open(candidate, encoding="utf-8") as fh:
                label_maps = json.load(fh).get("forced_label_map", {})
            map_source = why
            break
    if map_source != "answer tree" and any(a == "forced" for (_, a, _) in answers):
        print("jury: WARNING no _manifest.json in " + args.root + ". The forced arm is being"
              " decoded against the current packs, so if packs were rebuilt after those"
              " answers were collected, those numbers are meaningless. Snapshot"
              " packs/manifest.json into the answer tree when a round is run.")

    models = list_judges(args.root) or sorted({m for (m, _, _) in answers})
    # Arms come from what is actually on disk, not from a fixed list: a knockout run lands
    # in judges/<model>/knockout-7-sheet/ and silently scoring zero of it would be worse
    # than crashing.
    arms = sorted({a for (_, a, _) in answers if a != "forced"}) or list(ARMS)
    unknown = [a for a in arms if a not in ARMS and not a.startswith("knockout-")]
    if unknown:
        print("jury: scoring unexpected arm(s): " + ", ".join(unknown))
    rows, forced_rows, misses = [], [], []
    cell = {}  # (model, arm, case) -> hit, so the knockout can be read off directly

    for model in models:
        for arm in arms:
            got = tot = 0
            right_rule = 0
            for cid, case in cases.items():
                text = answers.get((model, arm, cid))
                if text is None:
                    continue
                tot += 1
                ok, missed = hit(text, case["key"])
                cell[(model, arm, cid)] = ok
                got += ok
                if not ok:
                    misses.append((model, arm, cid, missed))
                if arm.endswith("sheet") and claimed_rule(text) == case["target_rule"]:
                    right_rule += 1
            # A judge that answered nothing in a standard arm is still a row, showing 0,
            # because a judge that silently vanishes from the table is the failure mode
            # this whole repository is arguing against.
            if tot or arm in ARMS:
                rows.append((model, arm, got, tot, right_rule))

        for cid in cases:
            text = answers.get((model, "forced", cid))
            if text is None:
                continue
            forced_rows.append((model, cid, forced_pick(text, label_maps.get(cid, {}))))

    expected = len(models) * len(arms) * len(cases)
    present = sum(tot for _, _, _, tot, _ in rows)
    knock = knockout_rows(cell, cases, models)
    render_scores(rows, forced_rows, misses, cases, models, args.out,
                  coverage=(present, expected), knock=knock)
    for model, arm, got, tot, rule in rows:
        print(f"{model:44s} {arm:8s} {got}/{tot} hits   rule named right: {rule}")
    if forced_rows:
        wins = sum(1 for _, _, pick in forced_rows if pick == "sheet")
        print(f"forced choice: sheet picked in {wins}/{len(forced_rows)} judgements")
    print(f"\nwritten to {args.out}")
    return 0


def knockout_rows(cell, cases, models):
    """For each rule dropped, did the case that rule answers survive without it?

    load-bearing  the full sheet got it and the cut sheet did not
    not needed     both got it, so the rule is not what carried that answer
    no signal      the full sheet missed it too, so there was nothing to lose
    """
    out = []
    for (model, arm, cid), _ in sorted(cell.items()):
        if not arm.startswith("knockout-"):
            continue
        rule = arm.split("-")[1]
        full = cell.get((model, "sheet", cid))
        cut = cell[(model, arm, cid)]
        if full is None:
            verdict = "no baseline"
        elif full and not cut:
            verdict = "load-bearing"
        elif full and cut:
            verdict = "not needed here"
        elif not full and cut:
            verdict = "better without it"
        else:
            verdict = "no signal"
        out.append((model, rule, cid, full, cut, verdict))
    return out


def render_scores(rows, forced_rows, misses, cases, models, out="SCORES.md", coverage=None,
                  knock=None):
    lines = ["# Scores", "",
             "Generated by `jury.py score`. Every number here comes from the answer files in",
             "`judges/`, scored against the open key in `cases.json`. Nothing is self-reported.",
             "", "## Hit rate by arm", "",
             "| Judge | Arm | Hits | Cases | Named the right rule |", "|---|---|---|---|---|"]
    for model, arm, got, tot, rule in rows:
        named = str(rule) if arm.endswith("sheet") else "-"
        lines.append(f"| {model} | {arm} | {got} | {tot} | {named} |")

    if forced_rows:
        lines += ["", "## Forced choice", "",
                  "Three checklists, unlabelled as to origin, order shuffled per case and recorded",
                  "in `packs/manifest.json`. A judge that flatters cannot flatter here: it has to",
                  "pick one.", "", "| Judge | Case | Picked |", "|---|---|---|"]
        for model, cid, pick in forced_rows:
            lines.append(f"| {model} | {cid} | {pick or 'unreadable'} |")

    if misses:
        lines += ["", "## Misses, in full", "",
                  "What the answer failed to contain. Published because a sheet that only reports",
                  "its hits is advertising.", ""]
        for model, arm, cid, missed in misses:
            short = "; ".join("/".join(g[:2]) for g in missed)
            lines.append(f"- `{model}` `{arm}` {cid}: missing {short}")

    if knock:
        lines += ["", "## Knockout", "",
                  "One rule is dropped from the sheet, and the case that rule is supposed to",
                  "answer is put again. `load-bearing` means the full sheet got that case and the",
                  "cut sheet did not. `not needed here` means the answer survived without the",
                  "rule, so something else in the sheet carried it, and the rule's confidence is",
                  "claiming more than this corpus can show.", "",
                  "| Judge | Rule dropped | Case | Full sheet | Without it | Verdict |",
                  "|---|---|---|---|---|---|"]
        mark = {True: "hit", False: "miss", None: "-"}
        for model, rule, cid, full, cut, verdict in knock:
            lines.append(f"| {model} | {rule} | {cid} | {mark[full]} | {mark[cut]} | {verdict} |")

    if coverage:
        present, expected = coverage
        lines += ["", "## Coverage", "",
                  f"{present} of {expected} answer slots are filled. A slot is empty when the",
                  "model returned nothing for that prompt, which happens: the whole sheet plus a",
                  "report can exceed what a small free model accepts, and the bridge writes no",
                  "file when a call fails. An empty slot counts as neither a hit nor a miss.", ""]
        for model, arm, got, tot, _ in rows:
            if tot < len(cases):
                lines.append(f"- `{model}` `{arm}`: {tot} of {len(cases)} answered")

    lines += ["", "## What this does not measure", "",
              "Whether the rules are good engineering. It measures whether a judge handed the",
              "sheet reaches the decision that a documented failure says was missing. A rule can",
              "score here and still be wrong, and rules 8 and 20 score nothing because this",
              "corpus has no case for them.", ""]
    with open(os.path.join(HERE, out), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))


def cmd_selftest(args):
    """The scorer has to reject a fluent answer that says nothing. Prove it."""
    cases = {c["id"]: c for c in load_cases()}
    good = {
        "C1": "Create the lock as a mutex with priority inheritance enabled.",
        "C2": "Treat the uptime counter as wrapping and compare deadlines by unsigned subtraction, since a signed 32-bit counter at 10 ms will overflow.",
        "C5": "Budget writes against the part's rated program/erase endurance and batch them, wear-aware.",
    }
    waffle = ("This is a classic embedded reliability problem. The team should follow best"
              " practices, improve testing, and add more logging to understand the root cause.")
    failures = 0
    for cid, answer in good.items():
        ok, missed = hit(answer, cases[cid]["key"])
        if not ok:
            failures += 1
            print(f"FAIL {cid}: a correct answer scored as a miss, missing {missed}")
    for cid in cases:
        ok, _ = hit(waffle, cases[cid]["key"])
        if ok:
            failures += 1
            print(f"FAIL {cid}: empty waffle scored as a hit")
    print("selftest: " + ("ok" if not failures else f"{failures} failure(s)"))
    return 1 if failures else 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="jury.py", description=__doc__.splitlines()[0])
    p.add_argument("--version", action="version", version=f"jury.py {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("packs", help="build the blind prompt packs")
    sp.add_argument("--knockout", type=int, default=None, metavar="N",
                    help="drop rule N from the sheet before building")
    sp.add_argument("--easy", action="store_true",
                    help="use report_easy, which names the mechanism. Kept to reproduce the "
                         "first round, where every arm scored near the ceiling because of it")
    sp.set_defaults(func=cmd_packs)

    ss = sub.add_parser("score", help="score the answers in judges/ and write SCORES.md")
    ss.add_argument("--root", default="judges", help="answer tree to score (default judges)")
    ss.add_argument("--out", default="SCORES.md", help="file to write")
    ss.set_defaults(func=cmd_score)

    st = sub.add_parser("selftest", help="check the scorer rejects an answer that says nothing")
    st.set_defaults(func=cmd_selftest)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
