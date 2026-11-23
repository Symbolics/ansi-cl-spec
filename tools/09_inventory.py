#!/usr/bin/env python3
"""Step 9: generate dist/inventory.json (symbol -> location inventory) and dist/inventory.LICENSE.

One record per (symbol name, anchor location), i.e. per element with a data-symbol attribute.
Deterministic: records sorted by (symbol, path, anchor), fixed formatting, no timestamps other than
the OPF's dcterms:modified. Published under MS-PL (not under the edition's terms).

The licence text tools/data/MS-PL.txt is the verbatim SPDX text, fetched once from
  https://raw.githubusercontent.com/spdx/license-list-data/main/text/MS-PL.txt
  sha256 7a162b1da10f1c22db4c68f07bec4a8355259f8d4aab5b00a2b2bbd423d833dd
so builds are offline.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anchors import _FRAGMENT_SAFE, raw_id  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.site import slug as slugmod  # noqa: E402

from lxml import etree  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
X = "http://www.w3.org/1999/xhtml"
OPF_NS = "http://www.idpf.org/2007/opf"
DC = "http://purl.org/dc/elements/1.1/"

COPYRIGHT = "Copyright © 2026 Symbolics Pte Ltd"
SITE = "https://symbolics.github.io/ansi-cl-spec/"  # web edition base URL (tools/build_site.py)
# kinds of the anchors that are not dictionary-entry names (name -> kind); the generator fails
# on any other non-entry anchor so a new one is classified deliberately.
EXTRA_KINDS = {
    **{n: "lambda-list-keyword" for n in ("&allow-other-keys", "&aux", "&body", "&environment",
                                          "&key", "&optional", "&rest", "&whole")},
    **{n: "optimize-quality" for n in ("compilation-speed", "debug", "safety", "space", "speed")},
    **{n: "documentation-type" for n in ("compiler-macro", "structure", "variable")},
    "standard": "method-combination-type",
    "otherwise": "case-clause-key",
}
HEADINGS = {"{%s}h%d" % (X, i) for i in range(1, 7)}


def norm(s):
    return " ".join(s.split())


def fragment(anchor):
    """URL-safe fragment for ANCHOR (the raw id); same encoder as the book's own links."""
    return quote(anchor, safe=_FRAGMENT_SAFE)


def heading_info(h):
    """(secno, title, id) of a heading element."""
    secno = ""
    parts = []
    names = None
    for c in h:
        if isinstance(c.tag, str) and c.get("class") == "secno":
            secno = norm("".join(c.itertext()))
        elif isinstance(c.tag, str) and c.get("class") == "names":
            names = norm("".join(c.itertext()))
        elif isinstance(c.tag, str) and c.get("class") == "kind":
            pass
    if names is not None:
        return secno, names, h.get("id")
    txt = "".join(t for t in _text_without(h, "secno"))
    return secno, norm(txt), h.get("id")


def _text_without(h, cls):
    yield h.text or ""
    for c in h:
        if not (isinstance(c.tag, str) and c.get("class") == cls):
            yield "".join(c.itertext())
        yield c.tail or ""


def containing_heading(el):
    for a in el.iterancestors():
        if a.tag in HEADINGS:
            return a
        if a.tag == "{%s}section" % X:
            for c in a:
                if c.tag in HEADINGS:
                    return c
    return None


def read_edition(opf):
    t = etree.parse(str(opf))
    ns = {"o": OPF_NS, "dc": DC}
    title = t.xpath("//dc:title[@id='title']", namespaces=ns)
    title = title[0].text if title else t.xpath("//dc:title", namespaces=ns)[0].text
    mod = t.xpath("//o:meta[@property='dcterms:modified']", namespaces=ns)
    return {
        "title": norm(title),
        "identifier": t.xpath("//dc:identifier", namespaces=ns)[0].text.strip(),
        "modified": mod[0].text.strip() if mod else None,
        "source": norm(t.xpath("//dc:source", namespaces=ns)[0].text),
    }


def find_opf(src):
    c = etree.parse(str(Path(src) / "META-INF" / "container.xml"))
    for el in c.iter():
        if isinstance(el.tag, str) and etree.QName(el).localname == "rootfile":
            return Path(src) / el.get("full-path")
    raise SystemExit("inventory: no rootfile in container.xml")


def build_records(oebps, cl_symbols, path_map):
    oebps = Path(oebps)
    legacy_of = {new: old for old, new in path_map.items()}
    recs = []
    for p in sorted(oebps.rglob("*.xhtml")):
        rel = p.relative_to(oebps).as_posix()
        tree = etree.parse(str(p), etree.XMLParser(resolve_entities=False, huge_tree=True))
        for el in tree.iter():
            if not isinstance(el.tag, str) or el.get("data-symbol") is None:
                continue
            name = norm(el.get("data-symbol"))
            anchor = el.get("id")
            if not anchor:
                raise SystemExit("inventory: %s: data-symbol %r has no id" % (rel, name))
            h3 = next((a for a in el.iterancestors()
                       if a.tag == "{%s}h3" % X and a.get("data-kind")), None)
            if h3 is not None:
                kind = h3.get("data-kind")
                head = h3
            else:
                kind = EXTRA_KINDS.get(name)
                if kind is None:
                    raise SystemExit("inventory: %s: unclassified non-entry anchor %r" % (rel, name))
                head = containing_heading(el)
                if head is None:
                    raise SystemExit("inventory: %s: no containing heading for %r" % (rel, name))
            secno, title, hid = heading_info(head)
            m = re.fullmatch(r"\(setf\s+(.+)\)", name)
            low = name.lower()
            rec = {"symbol": name,
                   "package": "COMMON-LISP" if low in cl_symbols or (m and m.group(1).lower() in cl_symbols) else None}
            if m:
                rec["setf"] = True
            rec.update({
                "kind": kind,
                "path": rel,
                "anchor": anchor,
                "href": rel + "#" + fragment(anchor),
                "short": slugmod.short(name, kind),
                "secno": secno,
                "title": title,
                "legacy": {"path": legacy_of.get(rel), "id": hid},
            })
            recs.append(rec)
    recs.sort(key=lambda r: (r["symbol"], r["path"], r["anchor"]))
    slugmod.check_unique(r["symbol"] for r in recs)
    return recs


def make_inventory(src, cl_symbols, path_map):
    src = Path(src)
    opf = find_opf(src)
    recs = build_records(opf.parent, cl_symbols, path_map)
    by_kind = {}
    for r in recs:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    locs = {}
    for r in recs:
        locs[r["symbol"]] = locs.get(r["symbol"], 0) + 1
    cl = {r["symbol"].lower() for r in recs if r["package"] and not r.get("setf")}
    return {
        "format": "ansi-cl-spec-inventory",
        "format_version": 1,
        "edition": read_edition(opf),
        "license": "MS-PL",
        "license_file": "inventory.LICENSE",
        "copyright": COPYRIGHT,
        "site": SITE,
        "base": "path values (and the path part of href) are relative to the EPUB's OEBPS/ directory; "
                "site + href is the page and anchor in the web edition; "
                "site + short is the extension-less short link (precise: symbol and kind), see README; "
                "href fragments are URL-encoded, anchor is the raw id; legacy gives the file name and id "
                "in the original (pre-rename) edition",
        "counts": {
            "entries": len(recs),
            "symbols": len(locs),
            "cl_symbols": len(cl),
            "symbols_with_several_locations": sum(1 for n in locs.values() if n > 1),
            "by_kind": dict(sorted(by_kind.items())),
        },
        "entries": recs,
    }


def dumps(inv):
    """Stable formatting: header pretty-printed, one entry per line."""
    j = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=False)
    head = [(k, v) for k, v in inv.items() if k != "entries"]
    lines = ["{"]
    for k, v in head:
        lines.append(" %s: %s," % (j(k), json.dumps(v, ensure_ascii=False, indent=1).replace("\n", "\n ")))
    lines.append(' "entries": [')
    n = len(inv["entries"])
    for i, r in enumerate(inv["entries"]):
        lines.append("  " + j(r) + ("," if i < n - 1 else ""))
    lines += [" ]", "}"]
    return "\n".join(lines) + "\n"


def license_text(path):
    body = Path(path).read_text(encoding="utf-8")
    return COPYRIGHT + "\nThis licence applies to inventory.json.\n\n" + body


def generate(src, out_dir, symbols_file, path_map_file, license_file):
    syms = {l.strip().lower() for l in Path(symbols_file).read_text().splitlines() if l.strip()}
    pm = json.loads(Path(path_map_file).read_text())
    inv = make_inventory(src, syms, pm)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "inventory.json").write_text(dumps(inv), encoding="utf-8")
    (out / "inventory.LICENSE").write_text(license_text(license_file), encoding="utf-8")
    return inv


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=str(ROOT / "src"))
    ap.add_argument("--out-dir", default=str(ROOT / "dist"))
    ap.add_argument("--symbols", default=str(ROOT / "tools/data/cl-symbols.txt"))
    ap.add_argument("--path-map", default=str(ROOT / "tools/data/path-map.json"))
    ap.add_argument("--license", default=str(ROOT / "tools/data/MS-PL.txt"))
    a = ap.parse_args(argv)
    inv = generate(a.src, a.out_dir, a.symbols, a.path_map, a.license)
    c = inv["counts"]
    print("inventory: %d entries, %d symbols (%d CL), %d with several locations"
          % (c["entries"], c["symbols"], c["cl_symbols"], c["symbols_with_several_locations"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
