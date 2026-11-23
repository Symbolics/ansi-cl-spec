import sys
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from sitefixture import make_oebps  # noqa: E402
from tools.site import check, chrome, toc  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("build_site", Path(__file__).parent.parent / "tools" / "build_site.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

CAR = "text/14-conses/14.2.9-car.xhtml"
RPLACA = "text/14-conses/14.2.8-rplaca.xhtml"
SEC = "text/14-conses/14.2-dictionary.xhtml"
CH = "text/14-conses/index.xhtml"


@pytest.fixture()
def model(tmp_path):
    return toc.Toc.load(make_oebps(tmp_path))


def test_reading_order_excludes_cover(model):
    assert model.spine[0] == "text/cover.xhtml"
    assert model.order[0] == "text/front/legal.xhtml" and "text/cover.xhtml" not in model.order
    assert model.order[-1] == "text/26-glossary/b.xhtml"


def test_prev_next(model):
    assert model.prev("text/front/legal.xhtml") is None  # first page
    assert model.next("text/front/legal.xhtml") == "nav.xhtml"
    assert model.prev(CAR) == RPLACA and model.next(CAR) == "text/26-glossary/index.xhtml"
    assert model.next("text/26-glossary/b.xhtml") is None  # last page
    assert model.prev("text/cover.xhtml") is None and model.next("text/cover.xhtml") is None


def test_up(model):
    assert model.up(CAR) == SEC          # entry -> dictionary section
    assert model.up(SEC) == CH           # section -> chapter
    assert model.up(CH) == "nav.xhtml"   # chapter -> Contents
    assert model.up("text/front/legal.xhtml") == "nav.xhtml"
    assert model.up("nav.xhtml") is None
    assert model.up("text/26-glossary/a.xhtml") == "text/26-glossary/index.xhtml"
    assert model.up("text/cover.xhtml") == "nav.xhtml"


def test_ancestors_and_titles(model):
    assert [n.title for n in model.ancestors(SEC)] == ["14 Conses", "14.2 The Conses Dictionary"]  # whitespace normalised
    assert [n.title for n in model.ancestors(RPLACA)][-1] == "14.2.8 rplaca & rplacd"
    assert len(model.ancestors(CAR)) == 3
    assert model.ancestors("nav.xhtml") == [] and model.ancestors("text/cover.xhtml") == []
    assert model.title("nav.xhtml") == "Contents" and model.title("text/cover.xhtml") is None
    assert model.node(CAR).fragment == "car"
    assert [n.title for n in model.ancestors("text/26-glossary/b.xhtml")] == ["26 Glossary", "B"]


def test_primary_node_is_first_in_document_order(tmp_path):
    spine = ["nav.xhtml", "a.xhtml"]
    roots = [toc.Node("1 One", "a.xhtml#x"), toc.Node("2 Two", "a.xhtml#y")]
    assert toc.Toc(spine, roots).node("a.xhtml").title == "1 One"


def test_shorten():
    assert toc.shorten("14.2 Short title") == ("14.2 Short title", False)
    long_car = "14.2.9 car, cdr, caar, cadr, cdar, cddr, caaar, caadr, cadar, … — Accessor"
    assert toc.shorten(long_car) == ("14.2.9 car …", True)
    text, cut = toc.shorten("1.4.1.4 " + "word " * 30)
    assert cut and text.endswith(" …") and len(text) <= 64 and text.startswith("1.4.1.4 word")
    assert toc.shorten("Terms, " + "x" * 80)[0] == "Terms …"


def test_relpath():
    assert toc.relpath("nav.xhtml", CAR) == "../../nav.xhtml"
    assert toc.relpath("text/14-conses/index.xhtml#ch14", CAR) == "index.xhtml#ch14"
    assert toc.relpath("assets/site.css", "nav.xhtml") == "assets/site.css"
    assert toc.relpath("text/26-glossary/a.xhtml", CAR) == "../26-glossary/a.xhtml"


@pytest.fixture()
def site(tmp_path):
    oebps = make_oebps(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    for n in bs.DOWNLOADS:
        (dist / n).write_text('{"entries": []}' if n == "inventory.json" else n)
    return oebps, bs.build_site(oebps, dist, tmp_path / "site")


def test_chrome_on_entry_page(site):
    oebps, out = site
    src = (oebps / CAR).read_text()
    built = (out / CAR).read_text()
    root = etree.fromstring(built.encode())  # well-formed
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    assert built.count("<body") == 1
    assert 'name="viewport"' in built
    assert '<link rel="stylesheet" type="text/css" href="../../assets/site.css"/>' in built
    assert '<link rel="prev" href="14.2.8-rplaca.xhtml"/>' in built
    assert '<link rel="up" href="14.2-dictionary.xhtml"/>' in built
    assert '<link rel="next" href="../26-glossary/index.xhtml"/>' in built
    crumbs = root.xpath('//x:nav[@class="site-crumbs"]//x:li', namespaces=ns)
    assert ["".join(li.itertext()) for li in crumbs] == ["Contents", "14 Conses", "14.2 The Conses Dictionary",
                                                          "14.2.9 car …"]
    hrefs = root.xpath('//x:nav[@class="site-crumbs"]//x:a/@href', namespaces=ns)
    assert hrefs == ["../../nav.xhtml", "index.xhtml#ch14", "14.2-dictionary.xhtml#sec142"]
    cur = root.xpath('//x:nav[@class="site-crumbs"]//x:span[@aria-current="page"]', namespaces=ns)
    assert len(cur) == 1 and cur[0].get("title").startswith("14.2.9 car, cdr")
    assert root.xpath('//x:a[@class="site-title"]/@href', namespaces=ns) == ["../../index.html"]
    pager = root.xpath('//x:nav[@class="site-pager"]/x:a', namespaces=ns)
    assert [a.get("class") for a in pager] == ["site-prev", "site-up", "site-next"]
    assert "".join(pager[0].itertext()) == "← 14.2.8 rplaca & rplacd"
    assert "".join(pager[2].itertext()) == "26 Glossary →"
    assert root.xpath('//x:p[@class="site-notice"]//x:a/@href', namespaces=ns) == ["../front/legal.xhtml#legal-title"]
    # original content preserved verbatim around the splices
    body_src = src[src.index("<section>"):src.index("</body>")]
    assert body_src in built
    assert check.check_site(out)[0] == []


def test_chrome_depth_and_edges(site):
    _, out = site
    nav = (out / "nav.xhtml").read_text()
    etree.fromstring(nav.encode())
    assert 'href="assets/site.css"' in nav and 'class="site-title" href="index.html"' in nav
    assert 'rel="up"' not in nav and 'aria-current="page">Contents' in nav
    first = (out / "text/front/legal.xhtml").read_text()
    assert 'rel="prev"' not in first and 'class="site-prev"' not in first and 'rel="next" href="../../nav.xhtml"' in first
    last = (out / "text/26-glossary/b.xhtml").read_text()
    assert 'class="site-next"' not in last and 'rel="up" href="index.xhtml"' in last
    cover = (out / "text/cover.xhtml").read_text()
    etree.fromstring(cover.encode())
    assert "site-pager" not in cover and "site-crumbs" not in cover and "site-header" in cover
    land = (out / "index.html").read_text()
    assert 'href="assets/site.css"' in land


def test_build_is_deterministic(tmp_path):
    oebps = make_oebps(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    for n in bs.DOWNLOADS:
        (dist / n).write_text('{"entries": []}' if n == "inventory.json" else n)
    snap = []
    for name in ("a", "b"):
        out = bs.build_site(oebps, dist, tmp_path / name)
        snap.append({p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob("*") if p.is_file()})
    assert snap[0] == snap[1]


def test_splice_requires_markup():
    with pytest.raises(ValueError):
        chrome.add_chrome("<html/>", toc.Toc([], []), "x.xhtml", "T")


def test_title_escaping_in_header(site):
    oebps, _ = site
    m = toc.Toc.load(oebps)
    out = chrome.add_chrome("<html><head></head><body class='x'></body></html>".replace("'", '"'), m, "nav.xhtml", "A & <B>")
    assert "A &amp; &lt;B&gt;" in out


def test_check_catches_broken_link_fragment_and_malformed(site):
    _, out = site
    page = out / CAR
    good = page.read_text()
    page.write_text(good.replace("</section>", '<a href="nope.xhtml">x</a></section>'))
    errs, _ = check.check_site(out)
    assert any("nope.xhtml" in e and "no such file" in e for e in errs)
    page.write_text(good.replace("</section>", '<a href="index.xhtml#missing">x</a></section>'))
    errs, _ = check.check_site(out)
    assert any("no id 'missing'" in e for e in errs)
    page.write_text(good.replace("</section>", "<p></section>"))
    errs, _ = check.check_site(out)
    assert any("not well-formed" in e for e in errs)
    assert check.main([str(out)]) == 1
    page.write_text(good)
    assert check.main([str(out)]) == 0
