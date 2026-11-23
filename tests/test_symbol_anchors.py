import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("s03", Path(__file__).parent.parent / "tools" / "03_symbol_anchors.py")
s03 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s03)

SRC = ('<h3 id="DictEntry_x_1" class="entry"><span class="secno">1.1</span> '
       '<span class="names">char&lt;=, (setf documentation),  car</span> <span class="kind">Function</span></h3>\n'
       '<li><a href="x"><span class="names">car</span></a></li>')


def test_wrap_and_idempotent():
    new, n = s03.transform(SRC)
    assert n == 3
    assert ('<span class="names"><span id="char&lt;=" data-symbol="char&lt;=">char&lt;=</span>, '
            '<span id="(setf-documentation)" data-symbol="(setf documentation)">(setf documentation)</span>,  '
            '<span id="car" data-symbol="car">car</span></span>') in new
    assert new.endswith('<li><a href="x"><span class="names">car</span></a></li>')  # listing untouched
    assert s03.transform(new) == (new, 0)


def test_collision():
    import pytest
    with pytest.raises(s03.Collision):
        s03.transform('<p id="car"/>' + SRC)
