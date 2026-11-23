import importlib.util
import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).parent.parent / "tools"
spec = importlib.util.spec_from_file_location("build_site", TOOLS / "build_site.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

OPF = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:title id="title">ANSI Common Lisp</dc:title>
<dc:title id="subtitle">An edition &amp; more</dc:title>
<dc:source>dpANS3R, 1994</dc:source>
<meta property="dcterms:modified">2026-11-23T06:30:00Z</meta>
</metadata></package>
"""

# every relative link the landing page makes must exist in this fixture
PAGES = ("text/index/a.xhtml", "text/26-glossary/a.xhtml", "text/back/errata.xhtml",
         "text/14-conses/14.2.9-car.xhtml", "text/front/legal.xhtml")


def make(tmp_path):
    oebps = tmp_path / "OEBPS"
    for rel in PAGES:
        (oebps / rel).parent.mkdir(parents=True, exist_ok=True)
        (oebps / rel).write_text("<html/>")
    (oebps / "css").mkdir()
    (oebps / "css" / "book.css").write_text("body{}")
    (oebps / "css" / ".hidden").write_text("x")
    (oebps / "images").mkdir()
    (oebps / "images" / "cover.png").write_bytes(b"png")
    (oebps / "nav.xhtml").write_text("<html/>")
    (oebps / "content.opf").write_text(OPF)
    (oebps / "toc.ncx").write_text("<ncx/>")
    dist = tmp_path / "dist"
    dist.mkdir()
    for n in bs.DOWNLOADS:
        (dist / n).write_text(n)
    return oebps, dist


def test_site_layout_and_links(tmp_path):
    oebps, dist = make(tmp_path)
    out = bs.build_site(oebps, dist, tmp_path / "site")
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert "index.html" in files and "nav.xhtml" in files and "css/book.css" in files
    assert all(n in files for n in bs.DOWNLOADS)
    assert "content.opf" not in files and "toc.ncx" not in files and "css/.hidden" not in files
    assert (out / "text/14-conses/14.2.9-car.xhtml").read_bytes() == (oebps / "text/14-conses/14.2.9-car.xhtml").read_bytes()
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
