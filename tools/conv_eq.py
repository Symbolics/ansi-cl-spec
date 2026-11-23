#!/usr/bin/env python3
"""Convention 3a: "==" -> U+2261 where the TeX has \\EQ.

The conversion rendered the TeX macro \\EQ (typeset as the identity sign, "equivalent to") as "==" in the
Examples and Notes, and often dropped the space that followed it ("==(gcd x y)"). Replace it with the
identity sign and make sure it is followed by exactly the space \\EQ stands for when something follows
it directly ("≡ (gcd ...)"), the way U+2192 is spaced in the same blocks; whitespace that already follows
is left alone. All 214 "==" in the book are \\EQ (verified entry by entry: the per-entry counts of \\EQ in
the dpANS3R sources equal the per-file counts of "==" in the EPUB). Idempotent; --check reports only.
"""
import re
import sys

from convlib import rewrite_runs, run_cli


def transform(text, path=None):
    n = [0]

    def fn(run, stack, _):
        if "==" not in run:
            return run

        def sub(m):
            n[0] += 1
            nxt = run[m.end():m.end() + 1]
            return "≡" if nxt.isspace() else "≡ "

        return re.sub(r"==", sub, run)

    return rewrite_runs(text, fn), n[0]


if __name__ == "__main__":
    sys.exit(run_cli(transform, description=__doc__))
