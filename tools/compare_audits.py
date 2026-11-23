#!/usr/bin/env python3
"""Compare two audit runs (text findings.json and/or examples findings.json) and list regressions.

    python3 tools/compare_audits.py --text-before A/findings.json --text-after B/findings.json \
        --examples-before A/findings.json --examples-after B/findings.json

Text: per (secno, section label) ratio before/after; a drop is a regression (see the normaliser caveat in the report).
Examples: steps are paired by (secno, names, position in the entry); per class before/after counts and
transition table; a regression is a step that moves to a worse class (match < neutral < bad).
"""
import argparse
import collections
import json

RANK = {"match": 0, "impl-dependent": 1, "no-expectation": 1, "skipped": 1,
        "mismatch": 2, "error": 2, "unparsed": 2}


def _names(n):
    return n if isinstance(n, str) else ",".join(n)


def text_sections(path):
    d = json.load(open(path))
    out = {}
    for e in d["entries"]:
        seen = collections.Counter()
        for s in e["sections"]:
            seen[s["label"]] += 1
            out[(e["secno"], s["label"], seen[s["label"]])] = s["ratio"]
    return out


def example_steps(path):
    """{(secno, names): [class, ...]} with unparsed blocks appended as 'unparsed'."""
    out = {}
    for e in json.load(open(path)):
        cl = [s["class"] for s in e["steps"]] + ["unparsed"] * len(e.get("unparsed", []))
        out[(e["secno"], _names(e["names"]))] = cl
    return out


def compare_text(b, a):
    ds = lambda m: collections.Counter("1.0" if r >= 1 else "<1" for r in m.values())
    reg = [(k, b[k], a[k]) for k in b if k in a and a[k] < b[k]]
    imp = [(k, b[k], a[k]) for k in b if k in a and a[k] > b[k]]
    return {"n_before": len(b), "n_after": len(a), "exact_before": sum(r >= 1 for r in b.values()),
            "exact_after": sum(r >= 1 for r in a.values()), "missing": sorted(set(b) ^ set(a)),
            "improved": len(imp), "regressions": reg}


def compare_examples(b, a):
    flat = lambda m: collections.Counter(c for cl in m.values() for c in cl)
    trans, reg, changed = collections.Counter(), [], []
    for k in b:
        x, y = b[k], a.get(k, [])
        if len(x) == len(y):
            for i, (p, q) in enumerate(zip(x, y)):
                if p != q:
                    trans[(p, q)] += 1
                    if RANK[q] > RANK[p]:
                        reg.append((k, i, p, q))
        elif x != y:  # step list changed length (e.g. a block that was unparsed now parses): compare per entry
            cx, cy = collections.Counter(x), collections.Counter(y)
            changed.append((k, dict(cx), dict(cy)))
            if sum(v for c, v in cy.items() if RANK[c] == 2) > sum(v for c, v in cx.items() if RANK[c] == 2) \
                    or cy["match"] < cx["match"]:
                reg.append((k, "entry-level", dict(cx), dict(cy)))
    return {"before": dict(flat(b)), "after": dict(flat(a)), "transitions": dict(trans),
            "entries_with_changed_step_list": changed, "regressions": reg}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-before"); ap.add_argument("--text-after")
    ap.add_argument("--examples-before"); ap.add_argument("--examples-after")
    a = ap.parse_args(argv)
    bad = 0
    if a.text_before and a.text_after:
        r = compare_text(text_sections(a.text_before), text_sections(a.text_after))
        print("TEXT", {k: v for k, v in r.items() if k not in ("regressions", "missing")})
        print("  sections on one side only:", r["missing"][:20])
        for x in r["regressions"]:
            print("  REGRESSION", x)
        bad += len(r["regressions"])
    if a.examples_before and a.examples_after:
        r = compare_examples(example_steps(a.examples_before), example_steps(a.examples_after))
        for k in ("before", "after", "transitions"):
            print("EXAMPLES", k, r[k])
        for c in r["entries_with_changed_step_list"]:
            print("  step list changed:", c)
        for x in r["regressions"]:
            print("  REGRESSION", x)
        bad += len(r["regressions"])
    print("regressions:", bad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
