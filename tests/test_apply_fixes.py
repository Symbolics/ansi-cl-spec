import json

import apply_fixes as af

DOC = '<?xml version="1.0"?>\n<html><body><p>a b c</p><p>x y</p></body></html>\n'


def make(tmp_path, fixes):
    d = tmp_path / "src" / "OEBPS"
    d.mkdir(parents=True)
    (d / "f.xhtml").write_text(DOC, encoding="utf-8")
    fj = tmp_path / "fixes.json"
    fj.write_text(json.dumps(fixes))
    return fj, d / "f.xhtml"


def run(tmp_path, fj, *extra):
    return af.main([str(fj), "--src", str(tmp_path / "src"), *extra])


def test_apply_check_idempotent(tmp_path):
    fj, f = make(tmp_path, [{"file": "OEBPS/f.xhtml", "old": "a b c", "new": "a B c"},
                             {"file": "OEBPS/f.xhtml", "old": "x y", "new": "x y z"}])
    assert run(tmp_path, fj, "--check") == 0 and f.read_text() == DOC
    assert run(tmp_path, fj) == 0
    assert f.read_text() == DOC.replace("a b c", "a B c").replace("x y", "x y z")
    after = f.read_text()
    patched, applied, already, problems = af.plan(json.loads(fj.read_text()), tmp_path / "src")
    assert (applied, already, problems) == ([], [0, 1], [])
    assert run(tmp_path, fj) == 0 and f.read_text() == after


def test_abort_without_writing(tmp_path):
    fj, f = make(tmp_path, [{"file": "OEBPS/f.xhtml", "old": "a b c", "new": "Q"},
                             {"file": "OEBPS/f.xhtml", "old": "<p>", "new": "<q>"}])  # not unique
    assert run(tmp_path, fj) == 1 and f.read_text() == DOC


def test_overlap_and_malformed(tmp_path):
    fj, f = make(tmp_path, [{"file": "OEBPS/f.xhtml", "old": "a b", "new": "1"},
                             {"file": "OEBPS/f.xhtml", "old": "b c", "new": "2"}])
    assert run(tmp_path, fj) == 1 and f.read_text() == DOC
    fj.write_text(json.dumps([{"file": "OEBPS/f.xhtml", "old": "a b c", "new": "<i>"}]))
    assert run(tmp_path, fj) == 1 and f.read_text() == DOC
