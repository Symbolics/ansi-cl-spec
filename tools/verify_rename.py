#!/usr/bin/env python3
"""Prove the rename rewrite is pure.

For every file: take the v0-original version, re-express each href/src value for the file's
new location using an independent implementation (urllib-based), and assert the result is
byte-identical to the current file. Also checks the reference counts (regex vs lxml) and
that the OPF spine order is unchanged.
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
OEBPS = ROOT / "src" / "OEBPS"
MAP_FILE = ROOT / "tools" / "data" / "path-map.json"
BASE = "http://x/"
ATTR_SPLIT = re.compile(r'((?<=\s)(?:href|src)=")([^"]*)(")')


def git_show(rev, path):
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout.decode("utf-8")


def expected(orig, old_ref, new_ref, mapping):
    """Independent re-expression of every attribute value (segments between values untouched)."""
    parts = ATTR_SPLIT.split(orig)  # [text, open, value, close, text, ...]
    out = [parts[0]]
    for i in range(1, len(parts), 4):
        opener, value, closer, tail = parts[i:i + 4]
        u = urlsplit(value)
        if u.scheme or not u.path:
            new_value = value
        else:
            tgt = urlsplit(urljoin(BASE + old_ref, u.path)).path[1:]
            tgt = mapping.get(tgt, tgt)
            up = new_ref.count("/")
            # path from new_ref's directory to tgt
            a, b = new_ref.split("/")[:-1], tgt.split("/")
            k = 0
            while k < len(a) and k < len(b) - 1 and a[k] == b[k]:
                k += 1
            new_value = "../" * (len(a) - k) + "/".join(b[k:])
            if u.fragment or value.endswith("#"):
                new_value += "#" + u.fragment
        out += [opener, new_value, closer, tail]
    return "".join(out)


def lxml_refs(data):
    root = etree.fromstring(data)
    return [(e.tag, a) for e in root.iter() for a in ("href", "src") if e.get(a) is not None]


def spine(opf_text):
    root = etree.fromstring(opf_text.encode("utf-8"))
    ns = {"o": "http://www.idpf.org/2007/opf"}
    items = {i.get("id"): i.get("href") for i in root.findall(".//o:manifest/o:item", ns)}
    return [(r.get("idref"), items[r.get("idref")]) for r in root.findall(".//o:spine/o:itemref", ns)]


def main():
    mapping = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    inverse = {n: o for o, n in mapping.items()}
    files = ["nav.xhtml", "toc.ncx", "content.opf"] + sorted(inverse)
    bad, total_old, total_new = [], 0, 0
    for new_ref in files:
        old_ref = inverse.get(new_ref, new_ref)
        orig = git_show("v0-original", f"src/OEBPS/{old_ref}")
        cur = (OEBPS / new_ref).read_bytes().decode("utf-8")
        total_old += len(ATTR_SPLIT.findall(orig))
        total_new += len(ATTR_SPLIT.findall(cur))
        if len(lxml_refs(orig.encode())) != len(ATTR_SPLIT.findall(orig)):
            bad.append(f"{old_ref}: regex/lxml reference count differs")
        if expected(orig, old_ref, new_ref, mapping) != cur:
            bad.append(f"{new_ref}: not byte-identical to the mapped original")
    extra = sorted(p.relative_to(OEBPS).as_posix() for p in (OEBPS / "text").rglob("*") if p.is_file()
                   and p.relative_to(OEBPS).as_posix() not in inverse)
    if extra:
        bad.append(f"unexpected files in text/: {extra[:5]}")
    if total_old != total_new:
        bad.append(f"reference count changed: {total_old} -> {total_new}")
    old_spine = [(i, mapping.get(h, h)) for i, h in spine(git_show("v0-original", "src/OEBPS/content.opf"))]
    new_spine = spine((OEBPS / "content.opf").read_text(encoding="utf-8"))
    if old_spine != new_spine:
        bad.append("OPF spine order/targets changed")
    if bad:
        print("verify_rename: FAIL")
        print("\n".join(bad[:30]))
        return 1
    print(f"verify_rename: identical ({len(files)} files byte-identical to the mapped originals; "
          f"{total_new} href/src values unchanged in number; spine of {len(new_spine)} items unchanged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
