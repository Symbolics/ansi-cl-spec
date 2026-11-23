#!/usr/bin/env python3
"""Step 8: register the "Errata and Corrections" back-matter page and update the metadata.

The page src/OEBPS/text/back/errata.xhtml is a committed file. This script splices (targeted text
edits; everything else stays byte-identical):
  content.opf  - manifest item "errata" and its spine itemref after the last A-appendix item (before
                 the index); dc:description updated
  nav.xhtml    - toc entry between the Appendix and the Index
  toc.ncx      - navPoint between the Appendix and the Index, playOrder renumbered sequentially
  text/front/legal.xhtml - one sentence linking to the errata page in Source and Acknowledgements
Idempotent; --check writes nothing and exits 1 if anything still needs applying.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OEBPS = ROOT / "src" / "OEBPS"
HREF = "text/back/errata.xhtml"
TITLE = "Errata and Corrections"
INDEX_HREF = "text/index/nonalph.xhtml#index"

DESCRIPTION = ("A structured EPUB edition of the X3J13 draft proposed ANSI Common Lisp standard (dpANS3R), "
               "with per-symbol anchors and a machine-readable symbol inventory. Errors present in the draft "
               "are corrected and listed on the Errata and Corrections page. This is not the ANSI standard; "
               "the published standard is definitive, and this edition has no formal standing.")
LEGAL_SENTENCE = ' Corrections to the draft text are listed on the <a href="../back/errata.xhtml#errata-title">Errata and Corrections</a> page.'
LEGAL_ANCHOR = "dpANS3R is technically identical to dpANS3 (X3J13/94-101)."


def do_opf(t):
    t = re.sub(r"<dc:description>.*?</dc:description>", lambda m: "<dc:description>%s</dc:description>" % DESCRIPTION, t, count=1, flags=re.S)
    if 'id="errata"' not in t:
        last = None
        ids = []
        for m in re.finditer(r'<item id="([^"]*)" href="text/A-appendix/[^"]*"[^>]*/>\n', t):
            last = m
            ids.append(m.group(1))
        if not last:
            raise SystemExit("no A-appendix manifest item found")
        item = '<item id="errata" href="%s" media-type="application/xhtml+xml"/>\n' % HREF
        t = t[:last.end()] + item + t[last.end():]
        refs = list(re.finditer(r'<itemref idref="(%s)"[^>]*/>\n' % "|".join(map(re.escape, ids)), t))
        t = t[:refs[-1].end()] + '<itemref idref="errata"/>\n' + t[refs[-1].end():]
    return t


def do_nav(t):
    if 'href="%s' % HREF not in t:
        li = '<li><a href="%s#errata-title">%s</a></li>\n' % (HREF, TITLE)
        key = '<li><a href="%s">Index</a>' % INDEX_HREF
        if t.count(key) != 1:
            raise SystemExit("nav: Index entry not found")
        t = t.replace(key, li + key, 1)
    return t


def do_ncx(t):
    if 'id="np-errata"' not in t:
        np = ('<navPoint id="np-errata" playOrder="1"><navLabel><text>%s</text></navLabel>'
              '<content src="%s#errata-title"/>\n</navPoint>\n' % (TITLE, HREF))
        m = re.search(r'<navPoint id="[^"]*" playOrder="\d+"><navLabel><text>Index</text></navLabel><content src="%s"/>' % re.escape(INDEX_HREF), t)
        if not m:
            raise SystemExit("ncx: Index navPoint not found")
        t = t[:m.start()] + np + t[m.start():]
    counter = iter(range(1, 10 ** 7))
    return re.sub(r'(<navPoint id="[^"]*" playOrder=")\d+(")', lambda m: m.group(1) + str(next(counter)) + m.group(2), t)


def do_legal(t):
    if "errata.xhtml" not in t:
        if t.count(LEGAL_ANCHOR) != 1:
            raise SystemExit("legal: Source paragraph not found")
        t = t.replace(LEGAL_ANCHOR, LEGAL_ANCHOR + LEGAL_SENTENCE, 1)
    return t


FILES = (("content.opf", do_opf), ("nav.xhtml", do_nav), ("toc.ncx", do_ncx), ("text/front/legal.xhtml", do_legal))


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
