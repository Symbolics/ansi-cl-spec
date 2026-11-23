#!/usr/bin/env python3
"""Apply a fixes JSON (a list of {file, old, new, ...}; file relative to src/) to src/.

Each `old` must occur exactly once in its file (a fix whose `new` is already in place counts as
"already applied"). Overlapping fixes are rejected. Nothing is written unless every fix is valid
and every patched XHTML file parses with lxml. Fixes are spliced in from the end of each file.
--check is a dry run. Idempotent.

    python3 tools/apply_fixes.py audit/triage/fixes.json [--check] [--src src]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent


def plan(fixes, src):
    """Return (patched {path: text}, applied, already, problems)."""
    src = Path(src)
    by_file = collections.defaultdict(list)
    for i, fx in enumerate(fixes):
        by_file[fx["file"]].append((i, fx))
    patched, applied, already, problems = {}, [], [], []
    for rel, items in by_file.items():
        path = src / rel
        if not path.is_file():
            problems.append(f"{rel}: file not found")
            continue
        text = path.read_text(encoding="utf-8")
        spans = []
        for i, fx in items:
            old, new = fx["old"], fx["new"]
            n_old = text.count(old)
            n_new = text.count(new)
            if n_old == 0 and (new == "" or n_new >= 1):
                already.append(i)  # `old` is gone and the replacement is present
                continue
            if n_old >= 1 and new != old and old in new and n_new >= 1 and n_old == n_new * new.count(old):
                already.append(i)  # `old` survives only inside the replacement
                continue
            if n_old != 1:
                problems.append(f"{rel} [{fx.get('secno')}]: old occurs {n_old} times: {old[:70]!r}")
                continue
            a = text.index(old)
            spans.append((a, a + len(old), i, new))
        spans.sort()
        for p, q in zip(spans, spans[1:]):
            if p[1] > q[0]:
                problems.append(f"{rel}: fixes {p[2]} and {q[2]} overlap")
        if not spans:
            continue
        out = text
        for a, b, i, new in reversed(spans):
            out = out[:a] + new + out[b:]
            applied.append(i)
        if rel.endswith((".xhtml", ".html", ".xml", ".opf", ".ncx")):
            try:
                etree.fromstring(out.encode("utf-8"), etree.XMLParser(resolve_entities=False))
            except etree.XMLSyntaxError as e:
                problems.append(f"{rel}: not well-formed after fixes: {e}")
        patched[path] = out
    return patched, sorted(applied), sorted(already), problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fixes")
    ap.add_argument("--src", default=str(ROOT / "src"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    fixes = json.loads(Path(a.fixes).read_text(encoding="utf-8"))
    patched, applied, already, problems = plan(fixes, a.src)
    print(f"{len(fixes)} fixes: {len(applied)} to apply in {len(patched)} files, {len(already)} already applied, {len(problems)} problems")
    for p in problems:
        print("  PROBLEM", p)
    if problems:
        print("aborted; nothing written")
        return 1
    if not a.check:
        for path, text in patched.items():
            path.write_text(text, encoding="utf-8")
        print(f"wrote {len(patched)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
