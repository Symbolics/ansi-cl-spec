#!/usr/bin/env python3
"""Step 7: Dublin Core metadata, and the "Copyright and Use" front-matter page registration.

Splices (targeted text edits; everything else stays byte-identical):
  content.opf  - the Dublin Core part of <metadata>; manifest item "legal"; spine itemref after the cover
  nav.xhtml    - first entry of the toc, and a copyright-page landmark
  toc.ncx      - first navPoint, and playOrder renumbered sequentially
The page src/OEBPS/text/front/legal.xhtml is a committed file. Idempotent; --check writes nothing
and exits 1 if anything still needs applying.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OEBPS = ROOT / "src" / "OEBPS"
HREF = "text/front/legal.xhtml"

DC = """<!-- dc:date and dcterms:modified are placeholders for the build date; re-set them at the v1 tag. -->
<dc:identifier id="bookid">{uid}</dc:identifier>
<dc:title id="title">ANSI Common Lisp</dc:title>
<meta refines="#title" property="title-type">main</meta>
<dc:title id="subtitle">An edition of the draft proposed American National Standard for Programming Language Common Lisp</dc:title>
<meta refines="#subtitle" property="title-type">subtitle</meta>
<dc:creator id="x3j13">X3J13</dc:creator>
<meta refines="#x3j13" property="role" scheme="marc:relators">aut</meta>
<dc:contributor id="editor">Kent M. Pitman</dc:contributor>
<meta refines="#editor" property="role" scheme="marc:relators">edt</meta>
<dc:contributor id="producer">Symbolics Pte Ltd</dc:contributor>
<meta refines="#producer" property="role" scheme="marc:relators">bkp</meta>
<dc:publisher>Symbolics Pte Ltd</dc:publisher>
<dc:date>2026-11-23</dc:date>
<dc:language>en</dc:language>
<dc:type>Text</dc:type>
<dc:subject>Common Lisp</dc:subject>
<dc:subject>Programming languages</dc:subject>
<dc:source>Draft proposed American National Standard for Information Systems, Programming Language Common Lisp, X3J13/94-101R (dpANS3R), 1994</dc:source>
<dc:relation>ANSI X3.226-1994 (now INCITS 226-1994 [R2018])</dc:relation>
<dc:description>A structured EPUB edition of the X3J13 draft proposed ANSI Common Lisp standard (dpANS3R), with per-symbol anchors and a machine-readable symbol inventory. This is not the ANSI standard; the published standard is definitive, and this edition has no formal standing.</dc:description>
<dc:rights>Copyright © 2026 Symbolics Pte Ltd. All rights reserved. This edition may be copied and distributed only in complete and unmodified form, not for direct commercial advantage, and only with notice that copying, distribution, display or transmission is by permission of Symbolics Pte Ltd. Permission to make modified copies, to make partial copies, or to create derivative works is expressly not granted. Provided "as is", without warranty of any kind, express or implied.</dc:rights>
<meta property="dcterms:rightsHolder">Symbolics Pte Ltd</meta>
<meta property="dcterms:modified">2026-11-23T00:00:00Z</meta>
"""

META_RE = re.compile(r'(<metadata[^>]*>\n)(.*?)(?=<meta name="cover")', re.S)
UID_RE = re.compile(r'<dc:identifier id="bookid">([^<]*)</dc:identifier>')


def do_opf(t):
    if "<dc:publisher>" not in t:
        m = META_RE.search(t)
        uid = UID_RE.search(m.group(2)).group(1)
        t = t[:m.end(1)] + DC.format(uid=uid) + t[m.end(2):]
    if 'id="legal"' not in t:
        item = '<item id="legal" href="%s" media-type="application/xhtml+xml"/>\n' % HREF
        t = re.sub(r'(<item id="cover" [^>]*/>\n)', lambda m: m.group(1) + item, t, count=1)
    if 'idref="legal"' not in t:
        t = re.sub(r'(<itemref idref="cover"[^>]*/>\n)', lambda m: m.group(1) + '<itemref idref="legal"/>\n', t, count=1)
    return t


def do_nav(t):
    if 'href="%s"' % HREF not in t:
        li = '<li><a href="%s#legal-title">Copyright and Use</a></li>\n' % HREF
        t = re.sub(r'(<h1>Contents</h1>\n<ol>\n)', lambda m: m.group(1) + li, t, count=1)
        lm = '<li><a epub:type="copyright-page" href="%s">Copyright and Use</a></li>\n' % HREF
        t = re.sub(r'(<li><a epub:type="toc" [^\n]*\n)', lambda m: m.group(1) + lm, t, count=1)
    return t


def do_ncx(t):
    if 'id="np-legal"' not in t:
        np = ('<navPoint id="np-legal" playOrder="1"><navLabel><text>Copyright and Use</text></navLabel>'
              '<content src="%s#legal-title"/>\n</navPoint>\n' % HREF)
        t = t.replace("<navMap>\n", "<navMap>\n" + np, 1)
    counter = iter(range(1, 10 ** 7))
    return re.sub(r'(<navPoint id="[^"]*" playOrder=")\d+(")', lambda m: m.group(1) + str(next(counter)) + m.group(2), t)


FILES = (("content.opf", do_opf), ("nav.xhtml", do_nav), ("toc.ncx", do_ncx))


def apply(oebps, check=False):
    """Return the list of files that changed (or would change)."""
    changed = []
    for name, fn in FILES:
        p = Path(oebps) / name
        old = p.read_text(encoding="utf-8")
        new = fn(old)
        if new != old:
            changed.append(name)
            if not check:
                p.write_text(new, encoding="utf-8")
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if changes are needed")
    ap.add_argument("--oebps", default=str(OEBPS))
    a = ap.parse_args(argv)
    if not (Path(a.oebps) / HREF).exists():
        print("missing page: %s" % HREF, file=sys.stderr)
        return 2
    changed = apply(a.oebps, a.check)
    print(("would change: " if a.check else "changed: ") + (", ".join(changed) or "nothing (already applied)"))
    return 1 if (a.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
