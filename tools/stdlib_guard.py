#!/usr/bin/env python3
"""Fail if anything in this repository imports outside the standard library.

The claim "no install, no network, no dependencies" is in the README. A static badge
asserting it is worth nothing, so this checks it instead, and CI fails when it stops being
true. The allowed set comes from the running interpreter, not from a list someone has to
remember to update.

    python tools/stdlib_guard.py [path]
"""

from __future__ import annotations

import ast
import os
import sys

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "site-packages",
             "build", "dist", ".mypy_cache", ".pytest_cache"}


def local_modules(root):
    """Names importable from inside the repo itself, which are never a dependency."""
    names = set()
    for entry in os.listdir(root):
        path = os.path.join(root, entry)
        if entry in SKIP_DIRS:
            continue
        if entry.endswith(".py"):
            names.add(entry[:-3])
        elif os.path.isdir(path) and os.path.exists(os.path.join(path, "__init__.py")):
            names.add(entry)
    return names


def imported_modules(path):
    """Every top-level module name imported by one file, with its line."""
    with open(path, encoding="utf-8") as fh:
        try:
            tree = ast.parse(fh.read(), filename=path)
        except SyntaxError as exc:
            print(f"stdlib-guard: cannot parse {path}: {exc}", file=sys.stderr)
            return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name.split(".")[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            # A relative import never leaves the repository.
            if node.level == 0 and node.module:
                found.append((node.module.split(".")[0], node.lineno))
    return found


def main(argv):
    root = os.path.abspath(argv[1] if len(argv) > 1 else ".")
    allowed = set(sys.stdlib_module_names) | local_modules(root) | {"__future__"}
    offenders = []
    checked = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            checked += 1
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            for module, line in imported_modules(path):
                if module not in allowed:
                    offenders.append((rel, line, module))

    if offenders:
        print(f"stdlib-guard: {len(offenders)} import(s) outside the standard library")
        for rel, line, module in offenders:
            print(f"  {rel}:{line}  {module}")
        print("\nThe README claims this runs with no install. Either the claim or the import "
              "has to go.")
        return 1

    print(f"stdlib-guard: {checked} file(s) checked, every import is standard library "
          f"(Python {sys.version_info.major}.{sys.version_info.minor})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
