#!/usr/bin/env python3
"""Convention 1: ASCII math relations -> Unicode, in math only.

The conversion rendered TeX \\le/\\leq as "<=", \\ne/\\neq as "<>" and \\ge/\\geq as ">=" inside
italic math runs. Rewrite them as U+2264, U+2260, U+2265. Only text inside <i> is touched, never inside
<pre>, <code>, <a>, <b>, headings, titles or table cells (the Lisp functions <=, >=, /= and their names).
Spacing: whitespace on a side of the operator becomes a single space; no whitespace stays none.
Idempotent; --check reports only.
"""
import re
import sys

from convlib import rewrite_runs, run_cli

BLOCK = {"pre", "code", "a", "b", "h1", "h2", "h3", "h4", "title", "td", "th", "caption", "dt", "tt"}
REL = re.compile(r"(\s*)(&lt;&gt;|&lt;=|&gt;=)(\s*)")
GLYPH = {"&lt;&gt;": "≠", "&lt;=": "≤", "&gt;=": "≥"}


def transform(text, path=None):
    n = [0]

    def fn(run, stack, _):
        if "i" not in stack or BLOCK & set(stack):
            return run

        def sub(m):
            n[0] += 1
            return (" " if m.group(1) else "") + GLYPH[m.group(2)] + (" " if m.group(3) else "")
        return REL.sub(sub, run)

    return rewrite_runs(text, fn), n[0]


if __name__ == "__main__":
    sys.exit(run_cli(transform, description=__doc__))
