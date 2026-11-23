#!/usr/bin/env python3
"""Audit an unpacked EPUB source tree: links, ids, manifest, CL symbol coverage.

Exit status is non-zero when any error is found.
"""
import argparse
import json
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
XHTML = "http://www.w3.org/1999/xhtml"


def parse(path):
    return etree.parse(str(path), etree.XMLParser(resolve_entities=False, huge_tree=True))


def local(tag):
    return etree.QName(tag).localname if isinstance(tag, str) else ""


def find_opf(src):
    container = parse(src / "META-INF" / "container.xml")
    for el in container.iter():
        if local(el.tag) == "rootfile":
            return src / el.get("full-path")
    raise SystemExit("audit: no rootfile in META-INF/container.xml")


def split_ref(ref, base_file):
    """Resolve REF (found in BASE_FILE) to (path relative to src, fragment); None if external."""
    parts = urlsplit(ref)
    if parts.scheme or parts.netloc:
        return None
    path = unquote(parts.path)
    frag = unquote(parts.fragment) if parts.fragment else None
    if path == "":
        rel = base_file
    else:
        rel = posixpath.normpath(posixpath.join(posixpath.dirname(base_file), path))
    return rel, frag


def collect_ids(tree):
    ids, dups = set(), set()
    for el in tree.iter():
        i = el.get("id") if isinstance(el.tag, str) else None
        if i is None:
            continue
        if i in ids:
            dups.add(i)
        ids.add(i)
    return ids, dups


def audit(src, symbols=None, require_anchors=False):
    src = Path(src)
    errors = []
    opf_path = find_opf(src)
    opf_rel = opf_path.relative_to(src).as_posix()

    docs = {}  # rel path -> tree, for every XHTML/NCX/OPF file
    for p in sorted(src.rglob("*")):
        if p.is_file() and p.suffix in (".xhtml", ".ncx", ".opf"):
            rel = p.relative_to(src).as_posix()
            try:
                docs[rel] = parse(p)
            except etree.XMLSyntaxError as e:
                errors.append(f"{rel}: XML parse error: {e}")

    # (b) duplicate ids
    ids, n_dups = {}, 0
    for rel, tree in docs.items():
        ids[rel], dups = collect_ids(tree)
        for d in sorted(dups):
            n_dups += 1
            errors.append(f"{rel}: duplicate id {d!r}")

    # (c) manifest and spine
    manifest, spine = {}, []
    opf = docs.get(opf_rel)
    if opf is not None:
        for el in opf.iter():
            if local(el.tag) == "item":
                rel = split_ref(el.get("href"), opf_rel)[0]
                manifest[el.get("id")] = rel
                if not (src / rel).is_file():
                    errors.append(f"{opf_rel}: manifest item {el.get('id')!r} missing file {rel}")
            elif local(el.tag) == "itemref":
                spine.append(el.get("idref"))
        for idref in spine:
            if idref not in manifest:
                errors.append(f"{opf_rel}: spine idref {idref!r} not in manifest")
    in_manifest = set(manifest.values())
    n_xhtml = 0
    for rel in docs:
        if rel.endswith(".xhtml"):
            n_xhtml += 1
            if rel not in in_manifest:
                errors.append(f"{rel}: XHTML file not in manifest")

    # (a) internal links
    n_links = n_broken = 0

    def check(rel, ref):
        nonlocal n_links, n_broken
        r = split_ref(ref, rel)
        if r is None:
            return
        target, frag = r
        n_links += 1
        if not (src / target).is_file():
            n_broken += 1
            errors.append(f"{rel}: broken link {ref!r} (no file {target})")
        elif frag and target in ids and frag not in ids[target]:
            n_broken += 1
            errors.append(f"{rel}: broken fragment {ref!r} (no id {frag!r} in {target})")

    for rel, tree in docs.items():
        for el in tree.iter():
            t = local(el.tag)
            if rel.endswith(".xhtml"):
                if t in ("a", "area", "link") and el.get("href"):
                    check(rel, el.get("href"))
                elif t in ("img", "script", "audio", "video", "source") and el.get("src"):
                    check(rel, el.get("src"))
            elif rel.endswith(".ncx") and t == "content" and el.get("src"):
                check(rel, el.get("src"))

    # (d) coverage of CL symbols
    coverage = None
    if symbols is not None:
        anchored, headings, index = set(), set(), set()
        ns = {"x": XHTML}
        for rel, tree in docs.items():
            if not rel.endswith(".xhtml"):
                continue
            for v in tree.xpath("//*[@data-symbol]"):
                anchored.add(v.get("data-symbol").strip().lower())
            for h in tree.xpath("//x:h3[contains(concat(' ',@class,' '),' entry ')]"
                                "/x:span[contains(concat(' ',@class,' '),' names ')]", namespaces=ns):
                for n in "".join(h.itertext()).split(","):
                    headings.add(" ".join(n.split()).lower())
            parts = rel.split("/")
            if parts[-2:-1] == ["index"] or re.match(r"i-", parts[-1]):
                # only <b> entries directly followed by a link; bare group headings
                # (e.g. "Variable" with sub-entries) are not locators
                for b in tree.xpath("//x:b[following-sibling::*[1][self::x:a]]", namespaces=ns):
                    index.add(" ".join("".join(b.itertext()).split()).lower())
        syms = set(symbols)
        a, h, i = syms & anchored, syms & headings, syms & index
        coverage = {
            "total": len(syms),
            "anchored": len(a),
            "in_headings": len(h),
            "in_index": len(i),
            "index_only": len(i - h - a),
            "in_none": sorted(syms - a - h - i),
            "no_anchor": sorted(syms - a),
        }
        if require_anchors and coverage["no_anchor"]:
            errors.append(f"{len(coverage['no_anchor'])} CL symbols lack a data-symbol anchor")

    return {
        "xhtml_files": n_xhtml,
        "links_checked": n_links,
        "broken_links": n_broken,
        "duplicate_ids": n_dups,
        "coverage": coverage,
        "errors": errors,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", nargs="?", default=str(ROOT / "src"))
    ap.add_argument("--symbols", default=str(ROOT / "tools" / "data" / "cl-symbols.txt"))
    ap.add_argument("--require-anchors", action="store_true",
                    help="error if any CL symbol lacks a data-symbol anchor")
    ap.add_argument("--json", metavar="PATH", help="write a machine-readable report")
    a = ap.parse_args(argv)

    sp = Path(a.symbols)
    symbols = [l.strip() for l in sp.read_text().splitlines() if l.strip()] if sp.is_file() else None
    rep = audit(a.src, symbols, a.require_anchors)

    print(f"audit: {rep['xhtml_files']} XHTML files, {rep['links_checked']} internal links, "
          f"{rep['broken_links']} broken, {rep['duplicate_ids']} duplicate ids")
    c = rep["coverage"]
    if c:
        print(f"coverage of {c['total']} CL symbols: {c['anchored']} with data-symbol anchor, "
              f"{c['in_headings']} in entry headings, {c['in_index']} in index "
              f"({c['index_only']} index-only), {len(c['in_none'])} in none")
        if c["in_none"]:
            print("  in none: " + ", ".join(c["in_none"]))
    for e in rep["errors"][:50]:
        print("ERROR " + e)
    if len(rep["errors"]) > 50:
        print(f"... and {len(rep['errors']) - 50} more errors")
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(rep, indent=2) + "\n")
    print("audit: " + ("FAIL" if rep["errors"] else "OK"))
    return 1 if rep["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
