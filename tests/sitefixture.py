"""A small fake OEBPS tree (spine, nav, pages at several depths) for the site tests."""
from pathlib import Path

OPF = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title id="title">ANSI Common Lisp</dc:title>
<dc:title id="subtitle">An edition &amp; more</dc:title>
<dc:source>dpANS3R, 1994</dc:source>
<meta property="dcterms:modified">2026-11-23T06:30:00Z</meta>
</metadata>
<manifest>
<item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml"/>
<item id="legal" href="text/front/legal.xhtml" media-type="application/xhtml+xml"/>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="c14" href="text/14-conses/index.xhtml" media-type="application/xhtml+xml"/>
<item id="s142" href="text/14-conses/14.2-dictionary.xhtml" media-type="application/xhtml+xml"/>
<item id="e1" href="text/14-conses/14.2.8-rplaca.xhtml" media-type="application/xhtml+xml"/>
<item id="e2" href="text/14-conses/14.2.9-car.xhtml" media-type="application/xhtml+xml"/>
<item id="g" href="text/26-glossary/index.xhtml" media-type="application/xhtml+xml"/>
<item id="ga" href="text/26-glossary/a.xhtml" media-type="application/xhtml+xml"/>
<item id="gb" href="text/26-glossary/b.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine>
<itemref idref="cover"/><itemref idref="legal"/><itemref idref="nav"/><itemref idref="c14"/>
<itemref idref="s142"/><itemref idref="e1"/><itemref idref="e2"/>
<itemref idref="g"/><itemref idref="ga"/><itemref idref="gb"/>
</spine>
</package>
"""

LONG = "14.2.9 car, cdr, caar, cadr, cdar, cddr, caaar, caadr, cadar, caddr, cdaar, … — Accessor"

NAV = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">
<head><meta charset="utf-8"/><title>Contents</title><link rel="stylesheet" type="text/css" href="css/book.css"/></head>
<body class="contents">
<nav epub:type="toc" id="toc"><h1>Contents</h1>
<ol>
<li><a href="text/front/legal.xhtml#legal-title">Copyright and Use</a></li>
<li><a href="text/14-conses/index.xhtml#ch14">14 Conses</a>
<ol>
<li><a href="text/14-conses/14.2-dictionary.xhtml#sec142">14.2 The Conses
   Dictionary</a>
<ol>
<li><a href="text/14-conses/14.2.8-rplaca.xhtml#rplaca">14.2.8 rplaca &amp; rplacd</a></li>
<li><a href="text/14-conses/14.2.9-car.xhtml#car">%s</a></li>
</ol></li>
</ol></li>
<li><a href="text/26-glossary/index.xhtml#glos">26 Glossary</a>
<ol>
<li><a href="text/26-glossary/a.xhtml#A">A</a></li>
<li><a href="text/26-glossary/b.xhtml#B">B</a></li>
</ol></li>
</ol></nav>
<nav epub:type="landmarks" hidden="hidden"><ol><li><a href="text/cover.xhtml">Cover</a></li></ol></nav>
</body>
</html>
""" % LONG.replace("&", "&amp;")

PAGE = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">
<head>
<meta charset="utf-8"/>
<title>%(title)s</title>
<link rel="stylesheet" type="text/css" href="%(up)scss/book.css"/>
</head>
<body%(attrs)s>
<section><h3 id="%(id)s">%(title)s</h3><p><span id="cadr"/>Text <a href="%(self)s#%(id)s">self</a>.</p></section>
</body>
</html>
"""

PAGES = {  # path: (id, body attrs)
    "text/front/legal.xhtml": ("legal-title", ""),
    "text/14-conses/index.xhtml": ("ch14", ' class="chapter"'),
    "text/14-conses/14.2-dictionary.xhtml": ("sec142", ""),
    "text/14-conses/14.2.8-rplaca.xhtml": ("rplaca", ' class="entry"'),
    "text/14-conses/14.2.9-car.xhtml": ("car", ' class="entry"'),
    "text/26-glossary/index.xhtml": ("glos", ""),
    "text/26-glossary/a.xhtml": ("A", ' class="glossary"'),
    "text/26-glossary/b.xhtml": ("B", ' class="glossary"'),
    # linked from the landing page but outside the spine and contents
    "text/index/a.xhtml": ("ia", ' class="index"'),
    "text/back/errata.xhtml": ("errata-title", ""),
}

COVER = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en"><head><meta charset="utf-8"/><title>Cover</title><link rel="stylesheet" type="text/css" href="../css/book.css"/></head>
<body class="cover"><section><img src="../images/cover.png" alt="Cover"/></section></body>
</html>
"""


def make_oebps(root):
    oebps = Path(root) / "OEBPS"
    for rel, (i, attrs) in PAGES.items():
        f = oebps / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        up = "../" * (rel.count("/"))
        f.write_text(PAGE % {"title": "Page " + i, "up": up, "attrs": attrs, "id": i, "self": rel.rsplit("/", 1)[1]},
                     encoding="utf-8")
    (oebps / "text" / "cover.xhtml").write_text(COVER, encoding="utf-8")
    (oebps / "css").mkdir()
    (oebps / "css" / "book.css").write_text("body{}")
    (oebps / "css" / ".hidden").write_text("x")
    (oebps / "images").mkdir()
    (oebps / "images" / "cover.png").write_bytes(b"png")
    (oebps / "nav.xhtml").write_text(NAV, encoding="utf-8")
    (oebps / "content.opf").write_text(OPF, encoding="utf-8")
    (oebps / "toc.ncx").write_text("<ncx/>")
    return oebps
