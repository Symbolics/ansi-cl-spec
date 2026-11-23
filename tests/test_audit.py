import audit

CONTAINER = ('<?xml version="1.0"?><container version="1.0" '
             'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
             '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
             '</rootfiles></container>')


def page(body):
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>t</title></head>'
            f'<body>{body}</body></html>')


def make_tree(root, pages, manifest_extra=""):
    """PAGES maps path under OEBPS to body HTML; all are put in the manifest."""
    (root / "META-INF").mkdir(parents=True)
    (root / "META-INF" / "container.xml").write_text(CONTAINER)
    (root / "mimetype").write_text("application/epub+zip")
    items = ""
    for i, (path, body) in enumerate(pages.items()):
        f = root / "OEBPS" / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(page(body))
        items += f'<item id="p{i}" href="{path}" media-type="application/xhtml+xml"/>'
    (root / "OEBPS" / "content.opf").write_text(
        '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
        f'<manifest>{items}{manifest_extra}</manifest><spine><itemref idref="p0"/></spine></package>')
    return root


def run(root, **kw):
    return audit.audit(root, **kw)


def test_clean(tmp_path):
    r = run(make_tree(tmp_path, {"a.xhtml": '<a href="sub/b.xhtml#x">b</a>',
                                 "sub/b.xhtml": '<p id="x">x</p><a href="../a.xhtml">up</a>'}))
    assert r["errors"] == [] and r["links_checked"] == 2


def test_broken_file(tmp_path):
    r = run(make_tree(tmp_path, {"a.xhtml": '<a href="nope.xhtml">b</a>'}))
    assert r["broken_links"] == 1 and any("broken link" in e for e in r["errors"])


def test_broken_fragment(tmp_path):
    r = run(make_tree(tmp_path, {"a.xhtml": '<a href="b.xhtml#zzz">b</a>', "b.xhtml": '<p id="x"/>'}))
    assert r["broken_links"] == 1 and any("broken fragment" in e for e in r["errors"])


def test_duplicate_id(tmp_path):
    r = run(make_tree(tmp_path, {"a.xhtml": '<p id="d"/><p id="d"/>'}))
    assert r["duplicate_ids"] == 1


def test_percent_encoded_fragment(tmp_path):
    r = run(make_tree(tmp_path, {"a.xhtml": '<a href="b.xhtml#char%3C=">b</a>',
                                 "b.xhtml": '<p id="char&lt;="/>'}))
    assert r["errors"] == []


def test_manifest_problems(tmp_path):
    root = make_tree(tmp_path, {"a.xhtml": "<p/>"},
                     '<item id="gone" href="gone.xhtml" media-type="application/xhtml+xml"/>')
    (root / "OEBPS" / "orphan.xhtml").write_text(page("<p/>"))
    errs = run(root)["errors"]
    assert any("missing file" in e for e in errs)
    assert any("orphan.xhtml: XHTML file not in manifest" in e for e in errs)


def test_coverage_and_require_anchors(tmp_path):
    body = ('<h3 class="entry"><span class="names">car, <span data-symbol="cdr">cdr</span></span></h3>')
    root = make_tree(tmp_path, {"a.xhtml": body})
    syms = ["car", "cdr", "zzz"]
    c = run(root, symbols=syms)["coverage"]
    assert (c["anchored"], c["in_headings"], c["in_none"]) == (1, 2, ["zzz"])
    assert run(root, symbols=syms)["errors"] == []
    assert run(root, symbols=syms, require_anchors=True)["errors"]
