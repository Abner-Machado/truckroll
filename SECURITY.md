# Security

## Reporting

Use [private vulnerability reporting](https://github.com/Abner-Machado/truckroll/security/advisories/new)
on this repository. It reaches the maintainer without the report being public first. Please
do not open a public issue for something exploitable.

No bounty, and no promised response window. What you get is an honest answer about whether
it is a real problem and what will happen next.

## What the attack surface actually is

`jury.py` reads files and writes files. It makes no network call, installs nothing, runs no
shell, and imports only the standard library, which CI checks on every push. The one
subprocess call in `tools/check_reproducible.py` invokes this repository's own `jury.py`
with `sys.executable`.

The part worth thinking about: everything under `judges/` is text produced by language
models, and `cases.json` holds the key it is scored against. Both are **data**. The scorer
lowercases them, matches phrases, and reads an integer out of a `RULE: n` line. Nothing in
an answer file is executed, imported, or used to build a path. A finding that shows
otherwise is exactly what this file is for.

## What is out of scope

The rules in `TASTE.md` are engineering opinions about firmware, not a security control.
Disagreeing with one is an issue, not a vulnerability. The same goes for a judge's answer
being wrong: that is a measurement the repository publishes on purpose, including the
misses.
