#!/usr/bin/env python3
"""Step 3: wrap each name in an entry heading's `names` span in a per-symbol anchor span.

<span class="names">car, cdr</span>  ->
<span class="names"><span id="car" data-symbol="car">car</span>, <span id="cdr" data-symbol="cdr">cdr</span></span>

Targeted text splice; separators are preserved. Idempotent (headings that already carry
data-symbol spans are skipped). --check prints what would change and writes nothing.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anchors import name_to_data_symbol, name_to_id, xml_unescape  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / "src" / "OEBPS" / "text"

HEADING_RE = re.compile(r'(<h3 id="[^"]*" class="entry">.*?<span class="names">)(.*?)(</span>)', re.S)
ID_RE = re.compile(r'\sid="([^"]*)"')


class Collision(Exception):
    pass


def transform(text, label="<text>"):
    """Return (new_text, number_of_names_wrapped)."""
    existing = ID_RE.findall(text)
    seen = set(existing)
    count = 0

    def repl(m):
        nonlocal count
        inner = m.group(2)
        if "data-symbol" in inner:
            return m.group(0)
        parts = re.split(r"(,\s*)", inner)
        out = []
        for i, p in enumerate(parts):
            if i % 2:
                out.append(p)
                continue
            name = xml_unescape(p)
            ident = name_to_id(name)
            if ident in seen:
                raise Collision(f"{label}: id {ident!r} already present (name {name!r})")
            seen.add(ident)
            out.append(f'<span id="{ident}" data-symbol="{name_to_data_symbol(name)}">{p}</span>')
            count += 1
        return m.group(1) + "".join(out) + m.group(3)

    return HEADING_RE.sub(repl, text), count


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="dry run")
    ap.add_argument("--text-dir", default=str(TEXT))
    a = ap.parse_args(argv)
    files = names = 0
    for p in sorted(Path(a.text_dir).rglob("*.xhtml")):
        old = p.read_bytes().decode("utf-8")
        try:
            new, n = transform(old, str(p))
        except Collision as e:
            print("STOP:", e)
            return 2
        if new != old:
            files += 1
            names += n
            if not a.check:
                p.write_bytes(new.encode("utf-8"))
    print(f"03_symbol_anchors: {'would wrap' if a.check else 'wrapped'} {names} names in {files} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
