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
    anchor = "</p><p><b>compiler-macro-function</b>"
    new, n = s04.add_index_entry(t, "compiler-macro", anchor)
    assert n == 1 and "#compiler-macro\">documentation, (setf documentation)</a>.\n</p><p><b>compiler-macro-function" in new
    assert s04.add_index_entry(new, "compiler-macro", anchor) == (new, 0)


def test_variable_entry_before_kind_group():
    t = "</p><p><b>values-list</b>  x.\n</p><p><b>Variable</b> \n<br/>    <b>*</b>  y.\n"
    new, n = s04.add_index_entry(t, "variable", "</p><p><b>Variable</b>")
    assert n == 1
    assert new.index("<b>variable</b>") < new.index("<b>Variable</b>")
    assert '<b>variable</b>  <a href="../25-environment/25.2.15-documentation.xhtml#variable">' in new
    assert s04.add_index_entry(new, "variable", "</p><p><b>Variable</b>") == (new, 0)


def test_structure_link_and_anchor_move():
    t = s04.STRUCT_OLD + "</p><p><b>structure-class</b>  z.\n"
    new, n = s04.add_structure_link(t)
    assert n == 1
    assert '#SubSubSectio_Sharpsign_S_173">Sharpsign S</a>, \n<a href="../25-environment/25.2.15-documentation.xhtml#structure">documentation, (setf documentation)</a>.\n' in new
    assert s04.add_structure_link(new) == (new, 0)
    h = '<h4 id="X"><span id="structure" data-symbol="structure"></span><span class="secno">1</span></h4>'
    h2, k = s04.remove_span(h, s04.REMOVALS[0][1])
    assert k == 1 and h2 == '<h4 id="X"><span class="secno">1</span></h4>'
    assert s04.remove_span(h2, s04.REMOVALS[0][1]) == (h2, 0)
    # structure is placed in the doc-type list
    li = "<ul><li><b>structure</b> x</li></ul>"
    assert s04.place(li, r"<li>(?=<b>structure</b>)", ["structure"], "t")[1] == 1
