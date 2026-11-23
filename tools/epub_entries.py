#!/usr/bin/env python3
"""Parse EPUB dictionary-entry files (src/OEBPS/text/eN-M-K.xhtml) into entries."""
import re
import sys
from pathlib import Path

from lxml import etree

NS = "{http://www.w3.org/1999/xhtml}"
SECREF = "\u00a7"  # section/chapter link text is replaced by this marker


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
        if re.match(r"(s|c)\d", href) and re.match(r"(Figure\s+)?\d+(\.\d+|-\d+)*\s", "".join(el.itertext()).strip() + " "):
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


def parse_file(path):
    path = Path(path)
    tree = etree.parse(str(path))
    h3 = tree.find(f".//{NS}h3[@class='entry']")
    secno = h3.find(f"{NS}span[@class='secno']").text.strip()
    names = h3.find(f"{NS}span[@class='names']").text
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
        "file": path.name,
        "secno": secno,
        "chapter": int(secno.split(".")[0]),
        "id": h3.get("id"),
        "names": [" ".join(n.split()) for n in names.split(",") if n.strip()],
        "kind": " ".join(kind.split()),
        "sections": sections,
        "extra": extra,
    }


def parse_tree(textdir):
    files = sorted(Path(textdir).glob("e*-*-*.xhtml"))
    return [parse_file(f) for f in files if re.fullmatch(r"e\d+-\d+-\d+\.xhtml", f.name)]


if __name__ == "__main__":
    es = parse_tree(sys.argv[1])
    print(len(es), "entries")
