#!/usr/bin/env python3
"""Assemble the web edition (GitHub Pages site) from the EPUB source and the build outputs.

The site is the book's own XHTML, served unchanged, so a page URL is SITE + a path relative to
OEBPS/ (the same path as an inventory.json href). Web-only files are generated here and never
written into src/:

  index.html            landing page (generated)
  nav.xhtml css/ images/ text/   copied unchanged from src/OEBPS/
  ANSI-Common-Lisp.epub inventory.json inventory.LICENSE   copied from dist/ (run ./build.sh first)

Output is deterministic. The output directory is replaced.
"""
import argparse
import html
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://symbolics.github.io/ansi-cl-spec/"
COPY = ("nav.xhtml", "css", "images", "text")
DOWNLOADS = ("ANSI-Common-Lisp.epub", "inventory.json", "inventory.LICENSE")
REPO = "https://github.com/Symbolics/ansi-cl-spec"

INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<link rel="canonical" href="{site}"/>
<link rel="stylesheet" type="text/css" href="css/book.css"/>
<style>
body {{ max-width: 44em; margin: 0 auto; padding: 0 1em 2em; font-family: Georgia, "Times New Roman", serif; }}
ul.start li {{ margin: 0.35em 0; }}
.notice {{ font-size: 0.9em; margin-top: 2em; border-top: 1px solid rgba(128,128,128,0.4); padding-top: 0.8em; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p><i>{subtitle}</i></p>
<p>Derived from {source}. Edition of {modified}.</p>

<h2>Read</h2>
<ul class="start">
<li><a href="nav.xhtml">Contents</a></li>
<li><a href="text/index/a.xhtml">Index</a></li>
<li><a href="text/26-glossary/a.xhtml">Glossary</a></li>
<li><a href="text/back/errata.xhtml#errata-title">Errata and Corrections</a></li>
</ul>

<h2>Download</h2>
<ul class="start">
<li><a href="ANSI-Common-Lisp.epub">ANSI-Common-Lisp.epub</a>: the complete edition, for e-readers</li>
<li><a href="inventory.json">inventory.json</a>: symbol to page and anchor, for tools
(<a href="inventory.LICENSE">MS-PL</a>)</li>
</ul>

<h2>Linking to this edition</h2>
<p>Every page has a stable address: this site's address followed by the page's path, for example
<a href="text/14-conses/14.2.9-car.xhtml#cadr"><code>{site}text/14-conses/14.2.9-car.xhtml#cadr</code></a>.
Every Common Lisp symbol has its own anchor. <code>inventory.json</code> lists each symbol's <code>href</code>,
which is the path to append. Source: <a href="{repo}">{repo}</a>.</p>

<p class="notice">This is not the ANSI standard; the published standard, ANSI X3.226-1994, is definitive.
Copyright © 2026 Symbolics Pte Ltd. Copying, distribution, display or transmission of this edition is
by permission of Symbolics Pte Ltd; see <a href="text/front/legal.xhtml#legal-title">Copyright and Use</a>.</p>
</body>
</html>
"""


def opf_field(opf, pattern):
    m = re.search(pattern, opf, re.S)
    return html.unescape(m.group(1).strip()) if m else ""


def landing_page(oebps, site=SITE):
    opf = (Path(oebps) / "content.opf").read_text(encoding="utf-8")
    fields = {
        "title": opf_field(opf, r'<dc:title id="title">(.*?)</dc:title>'),
        "subtitle": opf_field(opf, r'<dc:title id="subtitle">(.*?)</dc:title>'),
        "source": opf_field(opf, r"<dc:source>(.*?)</dc:source>"),
        "modified": opf_field(opf, r'<meta property="dcterms:modified">(\d{4}-\d\d-\d\d)'),
    }
    esc = {k: html.escape(v, quote=False) for k, v in fields.items()}
    return INDEX.format(site=html.escape(site), repo=REPO, **esc)


def build_site(oebps, dist, out, site=SITE):
    oebps, dist, out = Path(oebps), Path(dist), Path(out)
    missing = [n for n in DOWNLOADS if not (dist / n).is_file()]
    if missing:
        raise SystemExit("build_site: missing %s in %s (run ./build.sh first)" % (", ".join(missing), dist))
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for name in COPY:
        src = oebps / name
        if src.is_dir():
            shutil.copytree(src, out / name, ignore=shutil.ignore_patterns(".*", "*~", "*.swp", "*.bak"))
        else:
            shutil.copyfile(src, out / name)
    for name in DOWNLOADS:
        shutil.copyfile(dist / name, out / name)
    (out / "index.html").write_text(landing_page(oebps, site), encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--oebps", default=str(ROOT / "src" / "OEBPS"))
    ap.add_argument("--dist", default=str(ROOT / "dist"))
    ap.add_argument("--out", default=str(ROOT / "dist" / "site"))
    ap.add_argument("--site", default=SITE, help="public base URL (for the canonical link)")
    a = ap.parse_args(argv)
    out = build_site(a.oebps, a.dist, a.out, a.site)
    n = sum(1 for p in out.rglob("*") if p.is_file())
    print("built site %s (%d files)" % (out, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
