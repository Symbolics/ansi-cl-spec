#!/usr/bin/env python3
"""Step 6: machine-readable markers on dictionary entries.

  <h3 id=".." class="entry" data-kind="system-class">      slug of the entry's kind
  <dt data-section="arguments-and-values"><b>Arguments and Values:</b></dt>   slug of the label

Only the existing start tags change (targeted splice). Only files that contain an entry heading are
touched. Idempotent; --check writes nothing and just reports the value counts.
"""
import argparse
import collections
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / "src" / "OEBPS" / "text"

H3_RE = re.compile(r'<h3 (id="[^"]*" class="entry")>((?:(?!</h3>).)*?<span class="kind">([^<]*)</span>.*?)</h3>', re.S)
DT_RE = re.compile(r"<dt>(<b>([^<]*?):</b></dt>)")


def slug(label):
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


def transform(text, kinds=None, sections=None):
    """Return (new_text, n_h3, n_dt). KINDS / SECTIONS are optional Counters."""
    if 'class="entry"' not in text:
        return text, 0, 0
    n = [0, 0]

    def h3(m):
        if "data-kind=" in m.group(0):
            return m.group(0)
        s = slug(m.group(3))
        n[0] += 1
        if kinds is not None:
            kinds[s] += 1
        return f'<h3 {m.group(1)} data-kind="{s}">{m.group(2)}</h3>'

    def dt(m):
        s = slug(m.group(2))
        n[1] += 1
        if sections is not None:
            sections[s] += 1
        return f'<dt data-section="{s}">{m.group(1)}'

    text = H3_RE.sub(h3, text)
    text = DT_RE.sub(dt, text)  # '<dt>' with no attributes only, so re-runs are no-ops
    return text, n[0], n[1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="dry run")
    ap.add_argument("--text-dir", default=str(TEXT))
    a = ap.parse_args(argv)
    kinds, sections = collections.Counter(), collections.Counter()
    nh = nd = nf = 0
    for p in sorted(Path(a.text_dir).rglob("*.xhtml")):
        old = p.read_bytes().decode("utf-8")
        new, h, d = transform(old, kinds, sections)
        if new != old:
            nf += 1
            nh += h
            nd += d
            if not a.check:
                p.write_bytes(new.encode("utf-8"))
    print(f"06_markers: {'would mark' if a.check else 'marked'} {nh} headings and {nd} dt elements in {nf} files")
    for title, c in (("data-kind", kinds), ("data-section", sections)):
        print(f"{title}:")
        for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {v:5d}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
