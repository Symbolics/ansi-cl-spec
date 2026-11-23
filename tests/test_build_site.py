import importlib.util
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
    return oebps, dist


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
