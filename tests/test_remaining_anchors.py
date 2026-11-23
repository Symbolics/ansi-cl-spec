import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("s04", Path(__file__).parent.parent / "tools" / "04_remaining_anchors.py")
s04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s04)


def test_place_heading_multiple_and_idempotent():
    t = '<h3 id="X_1"><span class="secno">3.4.4</span> Macro</h3>'
    new, n = s04.place(t, s04.heading("X_1"), ["&body", "&whole"], "t")
    assert n == 2
    assert new == ('<h3 id="X_1"><span id="&amp;body" data-symbol="&amp;body"></span>'
                   '<span id="&amp;whole" data-symbol="&amp;whole"></span><span class="secno">3.4.4</span> Macro</h3>')
    assert s04.place(new, s04.heading("X_1"), ["&body", "&whole"], "t") == (new, 0)


def test_place_lookahead():
    t = "<tr><td><b>debug</b></td><td><b>safety</b></td></tr>"
    new, n = s04.place(t, r"<td>(?=<b>safety</b>)", ["safety"], "t")
    assert new == '<tr><td><b>debug</b></td><td><span id="safety" data-symbol="safety"></span><b>safety</b></td></tr>'


def test_index_entry():
    t = "</p><p><b>compiler macro</b>  x.\n</p><p><b>compiler-macro-function</b>  y.\n"
    new, n = s04.add_index_entry(t)
    assert n == 1 and "#compiler-macro\">documentation, (setf documentation)</a>.\n</p><p><b>compiler-macro-function" in new
    assert s04.add_index_entry(new) == (new, 0)
