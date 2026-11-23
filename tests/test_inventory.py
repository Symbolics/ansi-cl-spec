import importlib.util
import json
from pathlib import Path

import pytest

import audit

TOOLS = Path(__file__).parent.parent / "tools"
spec = importlib.util.spec_from_file_location("s09", TOOLS / "09_inventory.py")
s09 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s09)

OPF = """<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">urn:uuid:abc</dc:identifier>
<dc:title id="title">Book</dc:title>
<dc:source>Src</dc:source>
<meta property="dcterms:modified">2026-01-02T00:00:00Z</meta>
</metadata>
<manifest><item id="a" href="text/1-x/1.2.1-car.xhtml" media-type="application/xhtml+xml"/>
<item id="b" href="text/1-x/1.2-s.xhtml" media-type="application/xhtml+xml"/>
<item id="c" href="text/1-x/1.2.2-doc.xhtml" media-type="application/xhtml+xml"/></manifest>
<spine><itemref idref="a"/></spine></package>
"""
CONTAINER = ('<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
             '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
             '</rootfiles></container>')


def page(body):
    return ('<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml"><head><title>t</title>'
            '</head><body>%s</body></html>' % body)


CAR = page('<section><h3 id="DictEntry_car_1" class="entry" data-kind="accessor"><span class="secno">1.2.1</span> '
           '<span class="names"><span id="car" data-symbol="car">car</span>, <span id="cadr" data-symbol="cadr">cadr</span>'
           '</span> <span class="kind">Accessor</span></h3><p>x</p></section>')
SEC = page('<section><h4 id="Sub_opt_9"><span id="&amp;optional" data-symbol="&amp;optional"></span>'
           '<span class="secno">1.2.3</span> Specifiers for  optional</h4></section>'
           '<section><h3 id="DictEntry_f_2" class="entry" data-kind="function"><span class="secno">1.2.9</span> '
           '<span class="names"><span id="speed" data-symbol="speed">speed</span></span></h3>'
           '<dl><dd><p><span id="otherwise" data-symbol="otherwise"></span>x</p></dd></dl></section>')
DOC = page('<section><h3 id="DictEntry_d_3" class="entry" data-kind="standard-generic-function"><span class="secno">1.2.2</span> '
           '<span class="names"><span id="documentation" data-symbol="documentation">documentation</span>, '
           '<span id="(setf-documentation)" data-symbol="(setf documentation)">(setf documentation)</span></span></h3></section>'
           '<section><h3 id="DictEntry_f_4" class="entry" data-kind="function"><span class="secno">1.2.4</span> '
           '<span class="names"><span id="*" data-symbol="*">*</span></span></h3></section>'
           '<section><h3 id="DictEntry_v_5" class="entry" data-kind="variable"><span class="secno">1.2.5</span> '
           '<span class="names"><span id="*" data-symbol="*">*</span></span></h3></section>')

PATH_MAP = {"text/e1-2-1.xhtml": "text/1-x/1.2.1-car.xhtml", "text/s1-2.xhtml": "text/1-x/1.2-s.xhtml",
            "text/e1-2-2.xhtml": "text/1-x/1.2.2-doc.xhtml"}
SYMS = {"car", "cadr", "&optional", "speed", "otherwise", "documentation", "*"}


def make(root):
    (root / "META-INF").mkdir(parents=True)
    (root / "META-INF" / "container.xml").write_text(CONTAINER)
    o = root / "OEBPS"
    (o / "text" / "1-x").mkdir(parents=True)
    (o / "content.opf").write_text(OPF)
    (o / "text/1-x/1.2.1-car.xhtml").write_text(CAR)
    (o / "text/1-x/1.2-s.xhtml").write_text(SEC)
    (o / "text/1-x/1.2.2-doc.xhtml").write_text(DOC)
    return root


def inv(root):
    return s09.make_inventory(root, SYMS, PATH_MAP)


def test_records(tmp_path):
    d = inv(make(tmp_path))
    e = {(r["symbol"], r["kind"]): r for r in d["entries"]}
    assert d["counts"]["entries"] == 9 == len(d["entries"])
    assert d["edition"] == {"title": "Book", "identifier": "urn:uuid:abc", "modified": "2026-01-02T00:00:00Z",
                            "source": "Src"}
    assert (d["license"], d["license_file"], d["format_version"]) == ("MS-PL", "inventory.LICENSE", 1)
    car = e[("cadr", "accessor")]
    assert car["path"] == "text/1-x/1.2.1-car.xhtml" and car["secno"] == "1.2.1" and car["title"] == "car, cadr"
    assert car["legacy"] == {"path": "text/e1-2-1.xhtml", "id": "DictEntry_car_1"} and car["package"] == "COMMON-LISP"
    opt = e[("&optional", "lambda-list-keyword")]
    assert opt["href"] == "text/1-x/1.2-s.xhtml#&optional" and opt["secno"] == "1.2.3"
    assert opt["title"] == "Specifiers for optional" and opt["legacy"]["id"] == "Sub_opt_9"
    assert opt["legacy"]["path"] == "text/s1-2.xhtml"
    # non-heading anchors take the containing entry
    assert e[("otherwise", "case-clause-key")]["secno"] == "1.2.9"
    assert e[("speed", "function")]["title"] == "speed"
    st = e[("(setf documentation)", "standard-generic-function")]
    assert st["setf"] is True and st["package"] == "COMMON-LISP" and st["anchor"] == "(setf-documentation)"
    assert st["href"].endswith("#(setf-documentation)")
    assert "setf" not in car
    # several locations for one symbol
    assert {r["kind"] for r in d["entries"] if r["symbol"] == "*"} == {"function", "variable"}
    assert d["counts"]["symbols"] == 8 and d["counts"]["symbols_with_several_locations"] == 1
    assert d["counts"]["cl_symbols"] == 7
    assert d["counts"]["by_kind"]["function"] == 2


def test_encoding():
    assert s09.fragment("(setf-x)") == "(setf-x)"
    assert s09.fragment("<=") == "%3C="
    assert s09.fragment("*print-base*") == "*print-base*"
    assert s09.fragment("char<") == "char%3C"


def test_unclassified_anchor_fails(tmp_path):
    make(tmp_path)
    p = tmp_path / "OEBPS/text/1-x/1.2-s.xhtml"
    p.write_text(p.read_text().replace('data-symbol="otherwise"', 'data-symbol="weird"'))
    with pytest.raises(SystemExit):
        inv(tmp_path)


def test_deterministic_and_license(tmp_path):
    make(tmp_path / "src")
    lic = tmp_path / "lic.txt"
    lic.write_text("LICENSE BODY\n")
    syms = tmp_path / "syms.txt"
    syms.write_text("\n".join(sorted(SYMS)) + "\n")
    pm = tmp_path / "pm.json"
    pm.write_text(json.dumps(PATH_MAP))
    outs = []
    for n in ("o1", "o2"):
        s09.generate(tmp_path / "src", tmp_path / n, syms, pm, lic)
        outs.append(((tmp_path / n / "inventory.json").read_bytes(), (tmp_path / n / "inventory.LICENSE").read_bytes()))
    assert outs[0] == outs[1]
    json.loads(outs[0][0])
    text = outs[0][1].decode()
    assert text.startswith("Copyright © 2026 Symbolics Pte Ltd\n") and "inventory.json" in text.split("\n")[1]
    assert text.endswith("\n\nLICENSE BODY\n")
    keys = [r["symbol"] for r in json.loads(outs[0][0])["entries"]]
    assert keys == sorted(keys)


def test_audit_inventory(tmp_path):
    make(tmp_path / "src")
    d = inv(tmp_path / "src")
    p = tmp_path / "inv.json"
    p.write_text(s09.dumps(d))
    syms = sorted(SYMS)
    r = audit.audit(tmp_path / "src", syms, False, p)
    assert r["inventory"]["records"] == 9 and not [e for e in r["errors"] if e.startswith("inventory")]
    d["entries"][0]["href"] = d["entries"][0]["path"] + "#nope"
    del d["entries"][1]
    p.write_text(s09.dumps(d))
    r = audit.audit(tmp_path / "src", syms, False, p)
    errs = [e for e in r["errors"] if e.startswith("inventory")]
    assert any("data-symbol elements" in e for e in errs) and any("inconsistent" in e or "resolve" in e for e in errs)
