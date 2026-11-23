import importlib.util
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location("s08", Path(__file__).parent.parent / "tools" / "08_errata_page.py")
s08 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s08)

OPF = """<package version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:description>old description</dc:description>
</metadata>
<manifest>
<item id="f1" href="text/1-x/index.xhtml" media-type="application/xhtml+xml"/>
<item id="f2" href="text/A-appendix/index.xhtml" media-type="application/xhtml+xml"/>
<item id="f3" href="text/A-appendix/A.1-y.xhtml" media-type="application/xhtml+xml"/>
<item id="f4" href="text/index/nonalph.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine toc="ncx">
<itemref idref="f1"/>
<itemref idref="f2"/>
<itemref idref="f3"/>
<itemref idref="f4"/>
</spine>
</package>
"""
NAV = """<ol>
<li><a href="text/1-x/index.xhtml#c">1 X</a></li>
<li><a href="text/A-appendix/index.xhtml#a">A Appendix</a>
<ol>
<li><a href="text/A-appendix/A.1-y.xhtml#s">A.1 Y</a></li>
</ol>
</li>
<li><a href="text/index/nonalph.xhtml#index">Index</a>
<ol>
<li><a href="text/index/a.xhtml#a">A</a></li>
</ol>
</li>
</ol>
"""
NCX = """<navMap>
<navPoint id="np1" playOrder="1"><navLabel><text>1 X</text></navLabel><content src="text/1-x/index.xhtml#c"/>
</navPoint>
<navPoint id="np2" playOrder="2"><navLabel><text>A Appendix</text></navLabel><content src="text/A-appendix/index.xhtml#a"/>
</navPoint>
<navPoint id="np3" playOrder="3"><navLabel><text>Index</text></navLabel><content src="text/index/nonalph.xhtml#index"/>
<navPoint id="np4" playOrder="4"><navLabel><text>A</text></navLabel><content src="text/index/a.xhtml#a"/></navPoint>
</navPoint>
</navMap>
"""
LEGAL = "<p>Text. dpANS3R is technically identical to dpANS3 (X3J13/94-101).</p>\n"


def make(tmp):
    (tmp / "text" / "front").mkdir(parents=True)
    (tmp / "text" / "back").mkdir(parents=True)
    (tmp / "text" / "back" / "errata.xhtml").write_text("x")
    (tmp / "text" / "front" / "legal.xhtml").write_text(LEGAL)
    for n, c in (("content.opf", OPF), ("nav.xhtml", NAV), ("toc.ncx", NCX)):
        (tmp / n).write_text(c)


def test_apply_and_idempotent(tmp_path):
    make(tmp_path)
    assert s08.main(["--oebps", str(tmp_path), "--check"]) == 1
    assert (tmp_path / "content.opf").read_text() == OPF
    assert s08.main(["--oebps", str(tmp_path)]) == 0
    opf = (tmp_path / "content.opf").read_text()
    assert "old description" not in opf and "Errata and Corrections page" in opf
    assert opf.index('id="f3"') < opf.index('id="errata"') < opf.index('id="f4"')
    assert opf.index('idref="f3"') < opf.index('idref="errata"') < opf.index('idref="f4"')
    nav = (tmp_path / "nav.xhtml").read_text()
    assert nav.index("A.1 Y") < nav.index("errata.xhtml#errata-title") < nav.index(">Index<")
    ncx = (tmp_path / "toc.ncx").read_text()
    assert re.findall(r'playOrder="(\d+)"', ncx) == ["1", "2", "3", "4", "5"]
    assert ncx.index("np2") < ncx.index("np-errata") < ncx.index("np3")
    legal = (tmp_path / "text" / "front" / "legal.xhtml").read_text()
    assert legal.count('href="../back/errata.xhtml#errata-title"') == 1
    before = {n: (tmp_path / n).read_text() for n in ("content.opf", "nav.xhtml", "toc.ncx", "text/front/legal.xhtml")}
    assert s08.main(["--oebps", str(tmp_path), "--check"]) == 0
    assert s08.main(["--oebps", str(tmp_path)]) == 0
    assert before == {n: (tmp_path / n).read_text() for n in before}
