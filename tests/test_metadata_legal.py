import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("s07", Path(__file__).parent.parent / "tools" / "07_metadata_legal.py")
s07 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s07)

OPF = """<?xml version="1.0"?>
<package version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">urn:uuid:abc</dc:identifier>
<dc:title>T</dc:title>
<meta property="dcterms:modified">2020-01-01T00:00:00Z</meta>
<meta name="cover" content="cover-image"/>
<meta property="schema:accessMode">textual</meta>
</metadata>
<manifest>
<item id="cover" href="text/cover.xhtml" media-type="application/xhtml+xml"/>
<item id="f0000" href="a.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine toc="ncx">
<itemref idref="cover" linear="yes"/>
<itemref idref="f0000"/>
</spine>
</package>
"""
NAV = """<body>
<nav epub:type="toc" id="toc">
<h1>Contents</h1>
<ol>
<li><a href="a.xhtml#x">1 A</a></li>
</ol>
</nav>
<nav epub:type="landmarks">
<ol>
<li><a epub:type="toc" href="nav.xhtml#toc">Contents</a></li>
</ol>
</nav>
</body>
"""
NCX = """<ncx>
<navMap>
<navPoint id="np1" playOrder="1"><navLabel><text>1 A</text></navLabel><content src="a.xhtml#x"/>
<navPoint id="np2" playOrder="2"><navLabel><text>1.1 B</text></navLabel><content src="a.xhtml#y"/>
</navPoint>
</navPoint>
</navMap>
</ncx>
"""


def make_fixture(tmp_path):
    (tmp_path / "text" / "front").mkdir(parents=True)
    (tmp_path / "text" / "front" / "legal.xhtml").write_text("x")
    for n, c in (("content.opf", OPF), ("nav.xhtml", NAV), ("toc.ncx", NCX)):
        (tmp_path / n).write_text(c)


def test_apply_and_idempotent(tmp_path):
    make_fixture(tmp_path)
    assert s07.main(["--oebps", str(tmp_path), "--check"]) == 1
    assert (tmp_path / "content.opf").read_text() == OPF
    assert s07.main(["--oebps", str(tmp_path)]) == 0
    opf = (tmp_path / "content.opf").read_text()
    assert "urn:uuid:abc" in opf and opf.count("dc:identifier") == 2
    assert 'name="cover"' in opf and "schema:accessMode" in opf and opf.count('property="dcterms:modified"') == 1
    assert opf.index('id="legal"') < opf.index('id="f0000"')
    assert opf.index('idref="cover"') < opf.index('idref="legal"') < opf.index('idref="f0000"')
    nav = (tmp_path / "nav.xhtml").read_text()
    assert nav.index("legal.xhtml#legal-title") < nav.index("1 A")
    assert 'epub:type="copyright-page"' in nav
    ncx = (tmp_path / "toc.ncx").read_text()
    import re
    assert re.findall(r'playOrder="(\d+)"', ncx) == ["1", "2", "3"]
    assert ncx.index("np-legal") < ncx.index("np1")
    before = {n: (tmp_path / n).read_text() for n in ("content.opf", "nav.xhtml", "toc.ncx")}
    assert s07.main(["--oebps", str(tmp_path), "--check"]) == 0
    assert s07.main(["--oebps", str(tmp_path)]) == 0
    assert before == {n: (tmp_path / n).read_text() for n in before}


def test_description_matches_errata_step():
    spec8 = importlib.util.spec_from_file_location("s08", Path(__file__).parent.parent / "tools" / "08_errata_page.py")
    s08 = importlib.util.module_from_spec(spec8)
    spec8.loader.exec_module(s08)
    assert "<dc:description>%s</dc:description>" % s08.DESCRIPTION in s07.DC
