"""Shared helpers for the tools/conv_*.py convention scripts: a tiny scanner over well-formed XHTML that
yields text runs with their open-element stack, plus the common --check / write driver. Edits are text
splices of the runs only, so everything else stays byte-identical."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / "src" / "OEBPS" / "text"
VOID = {"br", "hr", "img", "meta", "link", "input", "col", "area", "base", "wbr"}
TOKEN = re.compile(r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|<![^>]*>|<(/?)([A-Za-z][^\s/>]*)[^>]*?(/?)>", re.S)


def runs(text):
    """Yield (start, end, stack) for each text run (outside tags); stack = tuple of open element names."""
    stack, pos = [], 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            yield pos, m.start(), tuple(stack)
        pos = m.end()
        if m.group(2) is None:
            continue
        name = m.group(2).split(":")[-1].lower()
        if m.group(1):
            if name in stack:
                while stack and stack.pop() != name:
                    pass
        elif not m.group(3) and name not in VOID:
            stack.append(name)
    if pos < len(text):
        yield pos, len(text), tuple(stack)


def rewrite_runs(text, fn):
    """Apply fn(run_text, stack, abs_start) -> new run text to every text run; return the new text."""
    out, last = [], 0
    for a, b, stack in runs(text):
        new = fn(text[a:b], stack, a)
        if new != text[a:b]:
            out.append(text[last:a])
            out.append(new)
            last = b
    out.append(text[last:])
    return "".join(out)


def run_cli(transform, argv=None, description=""):
    """transform(text, path) -> (new_text, n_changes). Drives every src/OEBPS/text/**/*.xhtml."""
    import argparse
    from lxml import etree
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    ap.add_argument("--src", default=str(TEXT))
    a = ap.parse_args(argv)
    total, files = 0, 0
    for f in sorted(Path(a.src).rglob("*.xhtml")):
        s = f.read_text(encoding="utf-8")
        new, n = transform(s, f)
        if n:
            etree.fromstring(new.encode("utf-8"), etree.XMLParser(resolve_entities=False))
            total += n
            files += 1
            if not a.check:
                f.write_text(new, encoding="utf-8")
    print(f"{'would change' if a.check else 'changed'} {total} occurrence(s) in {files} file(s)")
    return 0
