#!/usr/bin/env python3
"""Compute the old -> new path map for the structural file-name scheme.

Writes tools/data/path-map.json (sorted; paths relative to src/OEBPS/) and prints
the entries whose names needed special handling.
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OEBPS = ROOT / "src" / "OEBPS"
MAP_FILE = ROOT / "tools" / "data" / "path-map.json"

SPELL_ALONE = {"+": "plus", "-": "minus", "*": "star", "/": "slash",
               "<": "lt", ">": "gt", "=": "eq"}
SPELL_MIXED = {"*": "star", "/": "slash", "<": "lt", ">": "gt"}
OCF_BAD = re.compile(r'[\x00-\x1f\x7f/"*:<>?\\ ]')


def slug(name):
    """Lossy, readable file-name slug for a (possibly HTML-escaped) name or title."""
    s = html.unescape(name).strip().lower()
    m = re.fullmatch(r"\(setf\s+(.+)\)", s)
    if m:
        return "setf-" + slug(m.group(1))
    m = re.fullmatch(r"\*(.*\w.*)\*", s)
    if m:
        s = m.group(1)
    if not re.search(r"[a-z0-9]", s):
        out = "-".join(SPELL_ALONE.get(c, "") for c in s if not c.isspace())
    else:
        out = "".join(f"-{SPELL_MIXED[c]}-" if c in SPELL_MIXED else c for c in s)
        out = re.sub(r"[^a-z0-9+=-]+", "-", out)
    return re.sub(r"-+", "-", out).strip("-")


def _first(pattern, text, path):
    m = re.search(pattern, text, re.S)
    if not m:
        raise SystemExit(f"rename_map: {pattern!r} not found in {path}")
    return m.group(1)


def split_title(title):
    secno, _, rest = html.unescape(title).partition(" ")
    return secno, rest


def build_map(text_dir):
    """Return (map, specials). Keys/values are 'text/...' paths relative to OEBPS."""
    text_dir = Path(text_dir)
    mapping, specials = {}, []
    chapter_dir = {}  # chapter number -> directory name

    def title_of(p):
        return _first(r"<title>(.*?)</title>", p.read_text(encoding="utf-8"), p)

    for p in sorted(q for q in text_dir.glob("c*.xhtml") if re.fullmatch(r"c(\d\d|A)", q.stem)):
        secno, rest = split_title(title_of(p))
        assert p.stem == "c" + secno.zfill(2) or p.stem == "c" + secno, (p, secno)
        d = f"{secno}-{slug(rest)}"
        chapter_dir[secno] = d
        mapping[f"text/{p.name}"] = f"text/{d}/index.xhtml"

    for p in sorted(text_dir.glob("s*.xhtml")):
        secno, rest = split_title(title_of(p))
        assert p.stem == "s" + secno.replace(".", "-"), (p, secno)
        mapping[f"text/{p.name}"] = f"text/{chapter_dir[secno.split('.')[0]]}/{secno}-{slug(rest)}.xhtml"

    for p in sorted(text_dir.glob("e*.xhtml")):
        text = p.read_text(encoding="utf-8")
        secno = _first(r'<h3 [^>]*class="entry"[^>]*><span class="secno">([^<]*)</span>', text, p)
        names = _first(r'<span class="names">([^<]*)</span>', text, p)
        first = names.split(", ")[0]
        assert p.stem == "e" + secno.replace(".", "-"), (p, secno)
        sl = slug(first)
        mapping[f"text/{p.name}"] = f"text/{chapter_dir[secno.split('.')[0]]}/{secno}-{sl}.xhtml"
        if re.search(r"[^a-z0-9-]", html.unescape(first)) or html.unescape(first) != sl:
            specials.append((secno, html.unescape(first), sl))

    for p in sorted(text_dir.glob("g-*.xhtml")):
        mapping[f"text/{p.name}"] = f"text/{chapter_dir['26']}/{p.stem[2:]}.xhtml"
    for p in sorted(text_dir.glob("i-*.xhtml")):
        mapping[f"text/{p.name}"] = f"text/index/{p.stem[2:]}.xhtml"
    mapping["text/cover.xhtml"] = "text/cover.xhtml"

    return dict(sorted(mapping.items())), specials


def check_map(mapping, text_dir=None):
    new = list(mapping.values())
    assert len(set(new)) == len(new), "duplicate target paths"
    assert len({n.lower() for n in new}) == len(new), "targets collide case-insensitively"
    for n in new:
        for part in n.split("/"):
            assert part and not OCF_BAD.search(part), f"invalid OCF name: {n}"
            assert not part.endswith("."), f"trailing dot: {n}"
    if text_dir is not None:
        want = {f"text/{p.name}" for p in Path(text_dir).glob("*.xhtml")}
        assert want == set(mapping), "map does not cover the flat text/ tree exactly"


def main():
    mapping, specials = build_map(OEBPS / "text")
    check_map(mapping, OEBPS / "text")
    MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    MAP_FILE.write_text(json.dumps(mapping, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(mapping)} files mapped -> {MAP_FILE.relative_to(ROOT)}")
    print(f"{len(specials)} entries with special name handling (secno, first name, slug):")
    for secno, name, sl in sorted(specials, key=lambda t: [int(x) if x.isdigit() else x for x in re.split(r"\.", t[0])]):
        print(f"  {secno:8} {name!r:45} -> {sl}")


if __name__ == "__main__":
    sys.exit(main())
