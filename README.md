# truckroll

Thirty-one decisions that decide whether embedded firmware survives the field, and a way
to check that the sheet actually earns them.

A devkit tolerates a lot. A board in a cabinet, updated over the air, powered by a supply
that sags, does not. The unit of failure out there is the truck roll: someone drives to the
device, because nothing else can reach it.

There is no shortage of firmware checklists. The problem with all of them, including the
first draft of this one, is that nobody can tell a good one from a plausible one. A list
asserts. So this repository ships the list and the test, and publishes the cases the
list does not catch.

## The claim, stated so it can fail

Given a de-identified report of a firmware failure that really happened, a reader handed
[TASTE.md](TASTE.md) names the decision that would have prevented it more often than a
reader handed a generic checklist, or nothing at all.

[jury.py](jury.py) measures that. Here is what it found, and it is not a clean win.

The sheet lifts a reader who does not already know the material, and does nothing for one
who does. On the same eight cases, a mid-sized model went from 2 hits out of 8 with no
sheet to 4 out of 8 with it, and a smaller one from 1 out of 8 to 2. A stronger model
scored 5 out of 8 either way: it already knew. Handed all three checklists unlabelled and
forced to choose, the judges picked this one in 23 of 24 judgements.

The first round of this test was worthless and is published anyway, in
[SCORES-easy.md](SCORES-easy.md). The incident reports named the mechanism, so the answer
was inside the question, every arm scored near the ceiling, and the sheet looked exactly as
useful as having no sheet at all. Rewriting the reports as symptoms only is what made the
difference measurable.

Knockout found something sharper than a score. Four rules are load-bearing: remove rule 3,
9, 19 or 24 and the case it covers stops being diagnosed. Three others, 7, 11 and 25, never
land: the sheet misses those cases even with the rule present, which is a problem with how
those three are written, not with whether they are right.

The numbers, the misses in full, and the raw answers are in [SCORES.md](SCORES.md) and
`judges/`. Re-run it against your own judge and the numbers will differ.

## How it is measured

Eight failures with a public record. Mars Pathfinder's priority inversion, the 787
generator counter that overflowed after 248 days, Ariane 501's unguarded conversion and
the exception handler that put a diagnostic word on the flight bus, the stack headroom
dispute in the Toyota throttle trial, the eMMC that wore out across a car fleet, 500 smart
locks bricked by an image built for another hardware revision, a thermostat update that
reported healthy and killed the battery two weeks later, and a signed-but-old firmware
image accepted by a bootloader. Sources and dates: [CASES.md](CASES.md).

The judge is told nothing about the product. Every case is rewritten as an anonymous
incident report. Name Pathfinder and any trained model recites "priority inversion" from
memory, and the test stops measuring the sheet. De-identified, it has to reason.

Three arms, one of them empty. Each case is put to the judge three times: with this
sheet, with a deliberately generic checklist, and with no checklist at all. The third arm
matters most, because a sheet that does not beat the reader's own knowledge is decoration.

Forced choice, because a free model flatters. Ask any model "is this good?" and it says
yes. So the fourth pack shows all three checklists under neutral labels and makes the judge
pick one. Flattery has nowhere to go in a forced choice against a control. The label order
is a balanced rotation, not a shuffle: shuffling eight cases put this sheet in the last
slot five times, and position bias in a model acting as judge is large enough to swamp the
effect being measured. The order is in `packs/manifest.json` and needs no seed to
reproduce.

Scored by an open key, not by self-report. `cases.json` holds, for each case, the
phrases an answer must contain. The scorer is deterministic, the key is in the repository,
and `python jury.py selftest` proves it rejects a fluent answer that says nothing. If a key
group is wrong, that is an issue worth opening.

Knockout, to price each rule. `python jury.py packs --knockout 7` rebuilds the sheet
without rule 7 and asks the same questions. A rule whose removal changes no answer is
carrying less weight than its confidence claims, and its confidence comes down. This is
where the number on each rule stops being an opinion.

## Use

```bash
python jury.py packs              # build the blind packs
python jury.py selftest           # check the scorer rejects empty answers
python jury.py score              # read judges/ and write SCORES.md
python jury.py packs --knockout 7 # drop a rule and ask again
```

Feed `packs/<arm>/<case>.txt` to whatever model you have and save its reply as
`judges/<your-model>/<arm>/<case>.txt`. That is the whole protocol. Python standard
library only: no install, no network, no key.

To use the sheet rather than test it, read [TASTE.md](TASTE.md) before a design review, or
put it in front of an agent that is about to write firmware. Mark each rule pass, fail or
not applicable, and write down why.

Confidence is how sure a rule is of itself, not how bad the failure is. A 0.95 is a law. A
0.75 is a rule reasonable engineers disagree about, and you should switch it off on purpose
if you disagree. The scope tag says where the rule even applies: `any`, `RTOS`, `OTA`,
`fleet`.

## What it is not

- Not a substitute for the datasheet, the errata sheet or the reference manual.
- Not a compliance claim. MISRA C, CERT C and IEC 61508 are their own work.
- Not a tutorial. It assumes you know what an ISR, a linker section and a bootloader are.
- Not a linter. It reads prose, not your repository. Some of these rules could be checked
  against a build; most need a human.
- Not a benchmark of models. The judge is instrumentation here, not the subject.

## What the test cannot tell you

Whether the rules are good engineering. It tells you whether the sheet moves a diagnosis
toward the decision a documented failure says was missing. A rule can score well here and
still be wrong, and two rules in the sheet score nothing at all because this corpus has no
case for them. Both facts are written down.

## License

MIT. See [LICENSE](LICENSE).

Abner Machado
