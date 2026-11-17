#!/usr/bin/env python3
"""Build the packs twice and fail if a single digest moves.

packs/*.txt is not committed: the manifest carries the digest of every prompt instead, so
the prompts are auditable only for as long as a rebuild produces the same bytes. The moment
that stops being true, SCORES.md describes prompts nobody can recover.

    python tools/check_reproducible.py
"""

from __future__ import annotations

import json
import subprocess
import sys

MANIFEST = "packs/manifest.json"


def build():
    out = subprocess.run([sys.executable, "jury.py", "packs"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print(out.stdout + out.stderr, file=sys.stderr)
        sys.exit(f"check_reproducible: jury.py packs exited {out.returncode}")
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    first = build()
    second = build()

    if first["sheet_digest"] != second["sheet_digest"]:
        sys.exit(f"the sheet digest moved: {first['sheet_digest']} -> {second['sheet_digest']}")

    if first["forced_label_map"] != second["forced_label_map"]:
        sys.exit("the forced-choice label order is not reproducible, so every forced result "
                 "in SCORES.md is undecodable")

    moved = sorted(k for k in set(first["pack_digests"]) | set(second["pack_digests"])
                   if first["pack_digests"].get(k) != second["pack_digests"].get(k))
    if moved:
        sys.exit("pack digests moved: " + ", ".join(moved[:10]))

    print(f"{len(second['pack_digests'])} packs rebuilt byte for byte, "
          f"sheet digest {second['sheet_digest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
