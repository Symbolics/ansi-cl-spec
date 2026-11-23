"""Machine-readable indexes for the web edition's scripts (written to the site root at build time).

search.json  (compact, deterministic; loaded lazily by assets/site.js)

  {"v": 1, "items": [[label, kind, href, type, full], ...]}

  label  text shown and matched (case-insensitive)
  kind   muted description: symbols "<inventory kind> · <secno>" (e.g. "function · 14.2.15"),
         sections "section", glossary terms "glossary"
  href   path relative to the site root, URL-encoded fragment (resolve against the site root)
  type   0 symbol (one item per inventory record), 1 section (table-of-contents node, secno + title,
         one per distinct href), 2 glossary term (only terms whose anchor exists)
  full   sections only: the complete title when `label` is shortened, else ""

  Order: symbols (by lower-cased name), sections (contents order), glossary terms (file order, then
  document order). The order is the final tie-break of the ranking, so keep it stable.
"""
import json
import re
from pathlib import Path
from urllib.parse import quote

from lxml import etree

from .toc import shorten

X = "{http://www.w3.org/1999/xhtml}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
GLOSSARY_DIR = "text/26-glossary"
SYMBOL, SECTION, GLOSSARY = 0, 1, 2


def _norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def glossary_terms(path):
    """[(term, id)] for a glossary page. A term's anchor is the id on its <dt>, else the last id in the
    preceding <dd> (the book places each term's anchor at the end of the previous entry)."""
    root = etree.parse(str(path)).getroot()
    out = []
    for dt in root.iter(X + "dt"):
        term = _norm("".join(dt.itertext()))
        if term.endswith(":"):
            term = term[:-1].rstrip()
        anchor = dt.get("id") or dt.get(XML_ID)
        if not anchor:
            prev = dt.getprevious()
            ids = [e.get("id") for e in prev.iter() if e.get("id")] if prev is not None else []
            anchor = ids[-1] if ids else None
        if term and anchor:
            out.append((term, anchor))
    return out


def build_search(oebps, toc, records):
    oebps = Path(oebps)
    items, seen = [], set()

    def add(label, kind, href, typ, full=""):
        key = (typ, label, href)
        if key in seen:
            return
        seen.add(key)
        items.append([label, kind, href, typ, full])

    for r in sorted(records, key=lambda r: (r["symbol"].lower(), r["symbol"], r["href"])):
        add(r["symbol"], "%s \u00b7 %s" % (r["kind"], r["secno"]), r["href"], SYMBOL)
    stack = list(reversed(toc.roots))
    while stack:
        n = stack.pop()
        stack.extend(reversed(n.children))
        short, cut = shorten(n.title)
        add(short, "section", n.href, SECTION, n.title if cut else "")
    gdir = oebps / GLOSSARY_DIR
    for f in sorted(gdir.glob("*.xhtml")) if gdir.is_dir() else []:
        for term, anchor in glossary_terms(f):
            add(term, "glossary", "%s/%s#%s" % (GLOSSARY_DIR, f.name, quote(anchor, safe="-_.~")), GLOSSARY)
    return {"v": 1, "items": items}


def write_search(oebps, out, toc, records):
    data = build_search(oebps, toc, records)
    path = Path(out) / "search.json"
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return data
