import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).parent))
from test_build_site import bs, make, CAR  # noqa: E402

JS = Path(__file__).parent.parent / "tools" / "site" / "assets" / "site.js"
X = "{http://www.w3.org/1999/xhtml}"


def build(tmp_path):
    oebps, dist = make(tmp_path)
    out = bs.build_site(oebps, dist, tmp_path / "site")
    return oebps, dist, out


def test_toc_json_structure(tmp_path):
    oebps, dist, out = build(tmp_path)
    data = json.loads((out / "toc.json").read_text(encoding="utf-8"))
    assert data["v"] == 1
    top = data["toc"]
    assert [n[0] for n in top] == ["Copyright and Use", "14 Conses", "26 Glossary"]
    assert len(top[0]) == 2  # leaf: no children array
    dictionary = top[1][2][0]
    assert dictionary[0] == "14.2 The Conses Dictionary" and dictionary[1] == "text/14-conses/14.2-dictionary.xhtml#sec142"
    assert [n[1] for n in dictionary[2]] == ["text/14-conses/14.2.8-rplaca.xhtml#rplaca", CAR + "#car"]
    assert dictionary[2][0][0] == "14.2.8 rplaca & rplacd"
    assert dictionary[2][1][0].startswith("14.2.9 car, cdr")  # full, not shortened
    assert [n[0] for n in top[2][2]] == ["A", "B"]


def test_toc_json_deterministic_and_checked(tmp_path):
    oebps, dist, out = build(tmp_path)
    first = (out / "toc.json").read_bytes()
    bs.build_site(oebps, dist, out)
    assert (out / "toc.json").read_bytes() == first
    assert bs.check.check_site(out)[0] == []
    bad = json.loads(first)
    bad["toc"][1][2][0][2].append(["Bad", "text/14-conses/14.2.9-car.xhtml#nope"])
    bad["toc"].append(["Gone", "text/gone.xhtml"])
    (out / "toc.json").write_text(json.dumps(bad), encoding="utf-8")
    errors = bs.check.check_site(out)[0]
    assert any("toc.json" in e and "no id 'nope'" in e for e in errors)
    assert any("toc.json" in e and "gone.xhtml" in e for e in errors)


def test_sidebar_slot_placement(tmp_path):
    oebps, dist, out = build(tmp_path)
    for page in (CAR, "nav.xhtml", "text/14-conses/index.xhtml", "text/26-glossary/a.xhtml"):
        text = (out / page).read_text(encoding="utf-8")
        assert text.count('class="site-sidebar"') == 1
        assert 'data-site-page="%s"' % page in text
        root = etree.parse(str(out / page)).getroot()  # still well-formed
        aside = root.find(".//%saside" % X)
        assert aside.get("hidden") == "hidden" and aside.get("data-site-page") == page
    for page in ("text/cover.xhtml", "index.html", "s/list.html", "s/cadr.html"):
        assert "site-sidebar" not in (out / page).read_text(encoding="utf-8"), page


NODE = r"""
const {findPath} = require(process.argv[2]);
const toc = [["A", "a.xhtml#x"],
  ["B", "b.xhtml#b", [["B1", "b1.xhtml", [["B1a", "b1a.xhtml#q"], ["B1b", "b1.xhtml#again"]]], ["B2", "b2.xhtml"]]],
  ["C", "b2.xhtml#dup"]];
console.log(JSON.stringify({
  top: findPath(toc, "a.xhtml"), self: findPath(toc, "b.xhtml"),
  deep: findPath(toc, "b1a.xhtml"), first: findPath(toc, "b2.xhtml"), dupe: findPath(toc, "b1.xhtml"),
  none: findPath(toc, "zzz.xhtml"), empty: findPath([], "a.xhtml"),
}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_find_path_in_node(tmp_path):
    script = tmp_path / "t.js"
    script.write_text(NODE, encoding="utf-8")
    r = subprocess.run(["node", str(script), str(JS)], capture_output=True, text=True, check=True)
    out = json.loads(r.stdout)
    assert out == {"top": [0], "self": [1], "deep": [1, 0, 0], "first": [1, 1], "dupe": [1, 0],
                   "none": None, "empty": None}
