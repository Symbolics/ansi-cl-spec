#!/usr/bin/env python3
"""Convention 3b: the math constant pi (TeX \\pi) -> U+03C0.

The conversion rendered $\\pi$ as the word "pi" padded with spaces, in italics (<i> pi </i>) or, in the
two-column tables of 12.2.21 and 2.3, as bare text. Replace the word with the Greek letter and drop the
padding the conversion added (none after '(' '-' '+' before it, none before '/', ')', ',', '.' or the
end of the run after it, "pi  i/2" -> "\u03c0i/2" as typeset); otherwise a run of spaces becomes one. Italic markup is kept as it was (<i>pi</i> -> <i>π</i>), nothing is added.
Never touched: the Lisp constant (text inside <pre>, <code>, <a>, <b>, headings, titles) and any
"pi" without surrounding whitespace (symbol tables such as <td>pi</td>).
Idempotent; --check reports only.
"""
import re
import sys

from convlib import rewrite_runs, run_cli

BLOCK = {"pre", "code", "a", "b", "h1", "h2", "h3", "h4", "title", "dt", "tt"}
PI = re.compile(r"(\s*)(?<![\w*+#'-])pi(?![\w*+#'-])(\s*)")


def _sub(m, run):
    before, after = m.group(1), m.group(2)
    if not before and not after:
        return m.group(0)
    s, e = m.start(), m.end()
    prevch = run[s - 1] if s > 0 else ""
    nxt = run[e] if e < len(run) else ""
    # before: padding is dropped at the start of the run and after ( - +, if any is left it is one space
    left = " " if (before and s > 0 and prevch not in "(-+") else ""
    # after: dropped at the end of the run, before / ) , . ; : and in "pi i/2"; otherwise one space
    if not after or nxt == "" or nxt in "/),.;:" or re.match(r"i/", run[e:]):
        right = ""
    else:
        right = " "
    return left + "\u03c0" + right


def transform(text, path=None):
    n = [0]

    def fn(run, stack, _):
        if BLOCK & set(stack) or "pi" not in run:
            return run

        def sub(m):
            r = _sub(m, run)
            if r != m.group(0):
                n[0] += 1
            return r
        return PI.sub(sub, run)

    return rewrite_runs(text, fn), n[0]


if __name__ == "__main__":
    sys.exit(run_cli(transform, description=__doc__))
