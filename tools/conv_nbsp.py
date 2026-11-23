#!/usr/bin/env python3
"""Convention 2: no-break spaces inside <pre>/<code> become ordinary spaces (U+0020).

Only text inside <pre> or <code> elements is touched (U+00A0 and its numeric character references);
no-break spaces elsewhere (prose, tables, headings) are left alone. Idempotent; --check reports only.
"""
import re
import sys

from convlib import rewrite_runs, run_cli

NB = re.compile(" |&#160;|&#[xX][aA]0;")


def transform(text, path=None):
    n = [0]

    def fn(run, stack, _):
        if "pre" not in stack and "code" not in stack:
            return run
        new, k = NB.subn(" ", run)
        n[0] += k
        return new

    return rewrite_runs(text, fn), n[0]


if __name__ == "__main__":
    sys.exit(run_cli(transform, description=__doc__))
