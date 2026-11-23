#!/usr/bin/env python3
"""Compare two EPUBs: same member names, byte-identical content."""
import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def compare(a, b):
    problems = []
    with zipfile.ZipFile(a) as za, zipfile.ZipFile(b) as zb:
        na = {n for n in za.namelist() if not n.endswith("/")}
        nb = {n for n in zb.namelist() if not n.endswith("/")}
        for n in sorted(na - nb):
            problems.append(f"only in {a}: {n}")
        for n in sorted(nb - na):
            problems.append(f"only in {b}: {n}")
        for n in sorted(na & nb):
            if za.read(n) != zb.read(n):
                problems.append(f"content differs: {n}")
        return problems, len(na & nb)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("built", nargs="?", default=str(ROOT / "dist" / "ANSI-Common-Lisp.epub"))
    ap.add_argument("original", nargs="?",
                    default=str(ROOT / "original" / "ANSI-Common-Lisp-2026-11-21.epub"))
    a = ap.parse_args(argv)
    problems, n = compare(a.built, a.original)
    for p in problems[:50]:
        print(p)
    print(f"roundtrip: {n} common members; " + ("FAIL" if problems else "identical"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
