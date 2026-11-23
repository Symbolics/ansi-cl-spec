import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).parent))
from test_build_site import bs, make, CAR, RPLACA  # noqa: E402

JS = Path(__file__).parent.parent / "tools" / "site" / "assets" / "site.js"
GLOSS = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en"><head><meta charset="utf-8"/><title>G</title></head>
<body class="glossary"><section><h3 id="A" class="letter">A</h3>
<dl><dt id="abort"><b>abort:</b></dt><dd> n. one.
<p><span id="fig-1"/><span id="absolute"/></p></dd><dt><b>absolute:</b></dt><dd> adj. two.
<p><span id="access"/></p></dd><dt><b>access:</b></dt><dd> three.</dd>
<dt><b>orphan:</b></dt><dd> no anchor before it? yes: none</dd></dl></section></body></html>
"""


def build(tmp_path):
    oebps, dist = make(tmp_path)
    (oebps / "text/26-glossary/a.xhtml").write_text(GLOSS, encoding="utf-8")
    out = bs.build_site(oebps, dist, tmp_path / "site")
    return oebps, out, json.loads((out / "search.json").read_text(encoding="utf-8"))


def test_search_json_contents(tmp_path):
    oebps, out, data = build(tmp_path)
    assert data["v"] == 1
    items = data["items"]
    by_type = {t: [i for i in items if i[3] == t] for t in (0, 1, 2)}
    assert len(by_type[0]) == 5
    assert ["list", "function · 14.2.8", RPLACA + "#rplaca", 0, ""] in items
    assert ["list", "system-class · 14.2.9", CAR + "#car", 0, ""] in items
    labels1 = [i[0] for i in by_type[1]]
    assert "14 Conses" in labels1 and "14.2 The Conses Dictionary" in labels1
    long = [i for i in by_type[1] if i[0].startswith("14.2.9")][0]
    assert long[0].endswith("…") and long[4].startswith("14.2.9 car, cdr")  # shortened, full kept
    # glossary: dt id, else last id of the preceding dd; terms without an anchor are skipped
    gl = {i[0]: i[2] for i in by_type[2]}
    assert gl == {"abort": "text/26-glossary/a.xhtml#abort",
                  "absolute": "text/26-glossary/a.xhtml#absolute",
                  "access": "text/26-glossary/a.xhtml#access"}  # "orphan" has no anchor: skipped
    keys = [(i[3], i[0], i[2]) for i in items]
    assert len(keys) == len(set(keys))  # no duplicates
    assert [i[0] for i in by_type[0]][:2] == ["&optional", "/="]  # lower-case name order, ASCII


def test_search_deterministic_and_checked(tmp_path):
    oebps, out, data = build(tmp_path)
    first = (out / "search.json").read_bytes()
    bs.build_site(oebps, tmp_path / "dist", out)
    assert (out / "search.json").read_bytes() == first
    assert bs.check.check_site(out)[0] == []
    # a bad anchor or file fails the check
    bad = json.loads(first)
    bad["items"].append(["x", "glossary", "text/26-glossary/a.xhtml#nope", 2, ""])
    bad["items"].append(["y", "section", "text/gone.xhtml", 1, ""])
    (out / "search.json").write_text(json.dumps(bad), encoding="utf-8")
    errors = bs.check.check_site(out)[0]
    assert any("no id 'nope'" in e for e in errors) and any("gone.xhtml" in e for e in errors)


def test_script_and_placeholder_on_pages(tmp_path):
    oebps, out, _ = build(tmp_path)
    assert (out / "assets/site.js").read_bytes() == JS.read_bytes()
    for page, src in ((CAR, "../../assets/site.js"), ("nav.xhtml", "assets/site.js"),
                      ("text/cover.xhtml", "../assets/site.js")):
        text = (out / page).read_text(encoding="utf-8")
        assert '<script src="%s" defer="defer"></script>' % src in text
        assert text.count('class="site-search" hidden="hidden"') == 1
        root = etree.parse(str(out / page)).getroot()
        assert root.find(".//{http://www.w3.org/1999/xhtml}header//{http://www.w3.org/1999/xhtml}div") is not None
        assert "<script>" not in text
    landing = (out / "index.html").read_text(encoding="utf-8")
    assert 'src="assets/site.js" defer="defer"' in landing and "site-search-landing" in landing
    chooser = (out / "s/list.html").read_text(encoding="utf-8")
    assert 'src="../assets/site.js"' in chooser and 'class="site-search"' in chooser
    assert "assets/site.js" not in (out / "s/cadr.html").read_text(encoding="utf-8")  # redirect page


NODE = r"""
const {rank} = require(process.argv[2]);
const items = [
  ["list", "function · 14.2.15", "a#1", 0, ""],
  ["list", "system-class · 4.4", "a#2", 0, ""],
  ["listen", "function · 1.1", "a#3", 0, ""],
  ["*print-base*", "variable · 22.1", "a#4", 0, ""],
  ["14.2 The Conses Dictionary", "section", "a#5", 1, ""],
  ["14.2.9 car, …", "section", "a#6", 1, "14.2.9 car, cdr, cadr, Accessor"],
  ["list", "glossary", "a#7", 2, ""],
  ["the list", "glossary", "a#8", 2, ""],
  ["Mylist", "function · 1.1", "a#9", 0, ""],
];
const h = (q) => rank(items, q, 20).map((i) => i[2]).join(",");
const out = {
  exact: h("LIST"),            // exact (symbols, then glossary), prefix, substring
  prefix: h("lis"),
  none: h("zzz"),
  empty: h("   "),
  bare: h("print-base"),       // leading * ignored for symbols
  secTitle: h("the conses"),   // section title without number
  secNum: h("14.2"),
  full: h("accessor"),         // shortened label, full title searchable
  limit: rank(items, "l", 2).length,
};
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_rank_in_node(tmp_path):
    script = tmp_path / "t.js"
    script.write_text(NODE, encoding="utf-8")
    r = subprocess.run(["node", str(script), str(JS)], capture_output=True, text=True, check=True)
    out = json.loads(r.stdout)
    assert out["exact"] == "a#1,a#2,a#7,a#3,a#9,a#8"
    assert out["prefix"] == "a#1,a#2,a#3,a#7,a#9,a#8"
    assert out["none"] == "" and out["empty"] == ""
    assert out["bare"] == "a#4"
    assert out["secTitle"] == "a#5"
    assert out["secNum"] == "a#6,a#5"  # both prefix: shorter label first
    assert out["full"] == "a#6"
    assert out["limit"] == 2
