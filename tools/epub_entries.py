#!/usr/bin/env python3
"""Parse EPUB dictionary-entry files into entries.

Entries are found by markup (any .xhtml under the text directory holding an `h3.entry` heading), so
this works on the renamed layout (`14-conses/14.2.9-car.xhtml`) and on the original flat one
(`e14-2-9.xhtml`).  Names may be wrapped in <span data-symbol> spans; only their text is used.
Reported file paths are relative to OEBPS/.
"""
import re
import sys
from pathlib import Path

from lxml import etree

NS = "{http://www.w3.org/1999/xhtml}"
SECREF = "\u00a7"  # section/chapter link text is replaced by this marker


def is_section_href(href):
    """True for a link to a section/chapter file: `s14-1.xhtml`/`c14.xhtml` (original layout) or
    `14-conses/14.1-cons-concepts.xhtml`/`14-conses/index.xhtml` (renamed layout), not glossary/index."""
    path = href.split("#", 1)[0]
    if re.match(r"(s|c)\d", href):
        return True
    if "26-glossary/" in path or "index/" in path:
        return False
    return bool(re.search(r"(^|/)(\d+(\.\d+)*-[^/]*|index)\.xhtml$", path))


def _tag(el):
    return el.tag.replace(NS, "") if isinstance(el.tag, str) else None


def element_text(el, out=None):
    """Plain text of el.  <pre> keeps its lines; links to sections/chapters
    (s*/c*.xhtml) become the marker SECREF; <p>/<br> become line breaks."""
    top = out is None
    if top:
        out = []
    tag = _tag(el)
    if tag == "a":
        href = el.get("href", "")
        if is_section_href(href) and re.match(r"(Figure\s+)?\d+(\.\d+|-\d+)*\s", "".join(el.itertext()).strip() + " "):
            out.append("Figure " + SECREF if "".join(el.itertext()).startswith("Figure") else SECREF)
            if el.tail:
                out.append(el.tail)
            return "".join(out) if top else None
    if tag == "pre":
        out.append("\n" + "".join(el.itertext()).strip("\n") + "\n")
    else:
        if tag in ("p", "br", "tr", "td", "th", "caption"):
            out.append("\n")
        if el.text:
            out.append(el.text)
        for ch in el:
            element_text(ch, out)
        if tag in ("p", "td", "th", "caption"):
            out.append("\n")
    if not top and el.tail:
        out.append(el.tail)
    return "".join(out) if top else None


def rel_to_oebps(path, text_dir=None):
    """Path of PATH relative to OEBPS/ (the parent of the `text` directory)."""
    path = Path(path)
    base = Path(text_dir) if text_dir else path.parent
    root = base.parent if base.name == "text" else base
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def find_entry_files(text_dir):
    """Files under TEXT_DIR (recursively) that contain an `h3.entry` heading, sorted by path."""
    out = []
    for p in sorted(Path(text_dir).rglob("*.xhtml")):
        b = p.read_bytes()
        if b"<h3" in b and re.search(rb'<h3\b[^>]*\bclass="entry"', b):
            out.append(p)
    return out


def parse_file(path, text_dir=None):
    path = Path(path)
    tree = etree.parse(str(path))
    h3 = tree.find(f".//{NS}h3[@class='entry']")
    secno = h3.find(f"{NS}span[@class='secno']").text.strip()
    names = "".join(h3.find(f"{NS}span[@class='names']").itertext())
    kind = h3.find(f"{NS}span[@class='kind']").text.strip()
    sections = []
    dl = h3.getnext()
    extra = []
    for node in tree.getroot().iter():
        if _tag(node) == "dl":
            dl = node
            break
    label = None
    for ch in dl:
        t = _tag(ch)
        if t == "dt":
            label = " ".join("".join(ch.itertext()).split()).rstrip(":")
        elif t == "dd":
            sections.append({"label": label, "text": element_text(ch).strip()})
        else:
            extra.append(t)
    return {
        "file": rel_to_oebps(path, text_dir),
        "secno": secno,
        "chapter": int(secno.split(".")[0]),
        "id": h3.get("id"),
        "names": [" ".join(n.split()) for n in names.split(",") if n.strip()],
        "kind": " ".join(kind.split()),
        "sections": sections,
        "extra": extra,
    }


def parse_tree(textdir):
    es = [parse_file(f, textdir) for f in find_entry_files(textdir)]
    es.sort(key=lambda e: ([int(x) if x.isdigit() else x for x in e["secno"].split(".")], e["file"]))
    return es


if __name__ == "__main__":
    es = parse_tree(sys.argv[1])
    print(len(es), "entries")
