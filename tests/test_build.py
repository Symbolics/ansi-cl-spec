import hashlib
import zipfile

import build

CONTAINER = ('<?xml version="1.0"?><container version="1.0" '
             'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
             '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
             '</rootfiles></container>')


def make_src(root):
    (root / "META-INF").mkdir(parents=True)
    (root / "OEBPS" / "text").mkdir(parents=True)
    (root / "mimetype").write_text("application/epub+zip")
    (root / "META-INF" / "container.xml").write_text(CONTAINER)
    (root / "OEBPS" / "text" / "b.xhtml").write_text("<p>b</p>")
    (root / "OEBPS" / "a.xhtml").write_text("<p>a</p>")
    (root / "OEBPS" / ".hidden").write_text("x")
    (root / "OEBPS" / "a.xhtml~").write_text("x")
    return root


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_deterministic(tmp_path):
    src = make_src(tmp_path / "src")
    build.build(src, tmp_path / "1.epub")
    build.build(src, tmp_path / "2.epub")
    assert sha(tmp_path / "1.epub") == sha(tmp_path / "2.epub")


def test_mimetype_first_stored_no_extra(tmp_path):
    out = build.build(make_src(tmp_path / "src"), tmp_path / "o.epub")
    with zipfile.ZipFile(out) as z:
        first = z.infolist()[0]
        assert first.filename == "mimetype"
        assert first.compress_type == zipfile.ZIP_STORED
        assert first.extra == b""
        assert all(i.compress_type == zipfile.ZIP_DEFLATED for i in z.infolist()[1:])
        names = [i.filename for i in z.infolist()[1:]]
        assert names == sorted(names)
        assert not any(".hidden" in n or n.endswith("~") for n in names)
        assert {i.date_time for i in z.infolist()} == {(1980, 1, 1, 0, 0, 0)}


def test_source_date_epoch(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1700000000")
    out = build.build(make_src(tmp_path / "src"), tmp_path / "o.epub")
    with zipfile.ZipFile(out) as z:
        assert z.infolist()[0].date_time[0] == 2023
