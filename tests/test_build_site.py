import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).parent.parent / "tools"
spec = importlib.util.spec_from_file_location("build_site", TOOLS / "build_site.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

sys.path.insert(0, str(Path(__file__).parent))
from sitefixture import make_oebps  # noqa: E402


def make(tmp_path):
    oebps = make_oebps(tmp_path)
    dist = tmp_path / "dist"
    dist.mkdir()
    for n in bs.DOWNLOADS:
        (dist / n).write_text(n)
    write_inventory(dist)
    return oebps, dist


def rec(symbol, kind, path, anchor, secno, title):
    return {"symbol": symbol, "kind": kind, "path": path, "anchor": anchor, "href": path + "#" + anchor,
            "short": bs.shortlinks.slugmod.short(symbol, kind), "secno": secno, "title": title}


CAR = "text/14-conses/14.2.9-car.xhtml"
RPLACA = "text/14-conses/14.2.8-rplaca.xhtml"
RECORDS = [
    rec("cadr", "accessor", CAR, "cadr", "14.2.9", "car, cdr, cadr"),
    rec("/=", "function", RPLACA, "rplaca", "14.2.8", "/="),
    rec("&optional", "lambda-list-keyword", CAR, "car", "14.2.9", "x"),
    rec("list", "system-class", CAR, "car", "14.2.9", "list"),
    rec("list", "function", RPLACA, "rplaca", "14.2.8", "list"),
]


def write_inventory(dist, records=RECORDS):
    (dist / "inventory.json").write_text(json.dumps({"entries": records}), encoding="utf-8")


def test_site_layout_and_links(tmp_path):
    oebps, dist = make(tmp_path)
    out = bs.build_site(oebps, dist, tmp_path / "site")
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert "index.html" in files and "nav.xhtml" in files and "css/book.css" in files
    assert all(n in files for n in bs.DOWNLOADS)
    assert "content.opf" not in files and "toc.ncx" not in files and "css/.hidden" not in files
    assert (out / "assets/site.css").is_file()
    book = (oebps / "text/14-conses/14.2.9-car.xhtml").read_text()
    built = (out / "text/14-conses/14.2.9-car.xhtml").read_text()
    assert built != book and 'id="car"' in built and "site-crumbs" in built
    index = (out / "index.html").read_text()
    for href in re.findall(r'href="([^"]+)"', index):
        if href.startswith("http"):
            continue
        assert (out / href.split("#")[0]).is_file(), href
    assert "An edition &amp; more" in index and "Edition of 2026-11-23" in index
    assert "by permission of Symbolics Pte Ltd" in index


def test_deterministic_and_replaces_output(tmp_path):
    oebps, dist = make(tmp_path)
    out = tmp_path / "site"
    out.mkdir()
    (out / "stale.txt").write_text("old")
    bs.build_site(oebps, dist, out)
    assert not (out / "stale.txt").exists()
    first = {p: p.read_bytes() for p in out.rglob("*") if p.is_file()}
    bs.build_site(oebps, dist, out)
    assert {p: p.read_bytes() for p in out.rglob("*") if p.is_file()} == first


def test_missing_downloads(tmp_path):
    oebps, dist = make(tmp_path)
    (dist / "inventory.json").unlink()
    with pytest.raises(SystemExit, match="run ./build.sh first"):
        bs.build_site(oebps, dist, tmp_path / "site")


def test_built_site_passes_check(tmp_path):
    oebps, dist = make(tmp_path)
    out = bs.build_site(oebps, dist, tmp_path / "site")
    errors, stats = bs.check.check_site(out)
    assert errors == [] and stats["pages"] >= 9


def test_short_pages(tmp_path):
    oebps, dist = make(tmp_path)
    out = bs.build_site(oebps, dist, tmp_path / "site")
    s = out / "s"
    # one precise page per record, one page per symbol, plus the list
    assert len(list(s.glob("*.html"))) == 5 + 4 + 1
    cadr = (s / "cadr.html").read_text()
    assert 'content="0; url=../text/14-conses/14.2.9-car.xhtml#cadr"' in cadr
    assert '<link rel="canonical" href="https://symbolics.github.io/ansi-cl-spec/text/14-conses/14.2.9-car.xhtml#cadr"/>' in cadr
    assert 'name="robots" content="noindex"' in cadr and "location.replace" in cadr
    assert "Go to cadr (accessor, 14.2.9)" in cadr
    assert (s / "cadr.accessor.html").read_text() == cadr
    assert "url=../%s#rplaca" % RPLACA in (s / "_sl=.html").read_text()
    chooser = (s / "list.html").read_text()
    assert "refresh" not in chooser and "../assets/site.css" in chooser
    assert chooser.index("14.2.8") < chooser.index("14.2.9")  # ordered by section number
    assert 'href="../%s#rplaca"' % RPLACA in chooser and 'href="../%s#car"' % CAR in chooser
    assert "url=../%s#rplaca" % RPLACA in (s / "list.function.html").read_text()
    assert "url=../%s#car" % CAR in (s / "list.system-class.html").read_text()
    idx = (s / "index.html").read_text()
    assert 'href="_sl=.html"' in idx and 'href="&amp;optional.html"' in idx and "list</a> (function, system-class)" in idx
    errors, _ = bs.check.check_site(out)
    assert errors == []


def test_short_pages_bad_inventory(tmp_path):
    oebps, dist = make(tmp_path)
    write_inventory(dist, RECORDS + [rec("CADR", "function", CAR, "cadr", "14.2.9", "x")])
    with pytest.raises(SystemExit, match="both map to"):
        bs.build_site(oebps, dist, tmp_path / "site")
    write_inventory(dist, [dict(RECORDS[0], short="s/other.accessor")])
    with pytest.raises(SystemExit, match="short"):
        bs.build_site(oebps, dist, tmp_path / "site")


def test_check_covers_meta_refresh(tmp_path):
    oebps, dist = make(tmp_path)
    out = bs.build_site(oebps, dist, tmp_path / "site")
    p = out / "s" / "cadr.html"
    p.write_text(p.read_text().replace("#cadr", "#nope", 1))
    errors, _ = bs.check.check_site(out)
    assert any("no id 'nope'" in e for e in errors)
    p.write_text(p.read_text().replace("14.2.9-car.xhtml#nope", "gone.xhtml"))
    errors, _ = bs.check.check_site(out)
    assert any("no such file" in e for e in errors)
