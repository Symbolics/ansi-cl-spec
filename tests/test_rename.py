import json

import pytest

from rename_apply import rewrite_text, rewrite_value
from rename_map import build_map, check_map, slug


@pytest.mark.parametrize("name,want", [
    ("car", "car"),
    ("1+", "1+"),
    ("char=", "char="),
    ("char&lt;=", "char-lt-="),
    ("*print-base*", "print-base"),
    ("*package*", "package"),
    ("(setf class-name)", "setf-class-name"),
    ("*", "star"),
    ("-", "minus"),
    ("+", "plus"),
    ("/", "slash"),
    ("=", "eq"),
    ("/=", "slash-eq"),
    ("&lt;=", "lt-eq"),
    ("&gt;", "gt"),
    ("Scope, Purpose, and History", "scope-purpose-and-history"),
    ("The Conses Dictionary", "the-conses-dictionary"),
])
def test_slug(name, want):
    assert slug(name) == want


MAPPING = {
    "text/c14.xhtml": "text/14-conses/index.xhtml",
    "text/e14-2-9.xhtml": "text/14-conses/14.2.9-car.xhtml",
    "text/e3-8-1.xhtml": "text/3-evaluation-and-compilation/3.8.1-x.xhtml",
    "text/g-a.xhtml": "text/26-glossary/a.xhtml",
    "text/cover.xhtml": "text/cover.xhtml",
}


def test_rewrite_value():
    # same directory -> bare file name, fragment preserved exactly
    assert rewrite_value("c14.xhtml#Chapter_X_1", "text/e14-2-9.xhtml", "text/14-conses/14.2.9-car.xhtml", MAPPING) \
        == "index.xhtml#Chapter_X_1"
    # other chapter
    assert rewrite_value("e3-8-1.xhtml", "text/e14-2-9.xhtml", "text/14-conses/14.2.9-car.xhtml", MAPPING) \
        == "../3-evaluation-and-compilation/3.8.1-x.xhtml"
    # css moves up two levels
    assert rewrite_value("../css/book.css", "text/e14-2-9.xhtml", "text/14-conses/14.2.9-car.xhtml", MAPPING) \
        == "../../css/book.css"
    # top-level files reference into text/ and keep other files
    assert rewrite_value("text/g-a.xhtml#a", "nav.xhtml", "nav.xhtml", MAPPING) == "text/26-glossary/a.xhtml#a"
    assert rewrite_value("css/book.css", "content.opf", "content.opf", MAPPING) == "css/book.css"
    # untouched forms
    assert rewrite_value("#frag", "text/c14.xhtml", "text/14-conses/index.xhtml", MAPPING) == "#frag"
    assert rewrite_value("https://example.org/x", "text/c14.xhtml", "text/14-conses/index.xhtml", MAPPING) \
        == "https://example.org/x"


def test_rewrite_text_touches_only_attribute_values():
    src = '<a  class="x" href="e14-2-9.xhtml#A">&lt;car&gt;\n</a>\n<link\n href="../css/book.css"/>'
    got = rewrite_text(src, "text/c14.xhtml", "text/14-conses/index.xhtml", MAPPING)
    assert got == src.replace('"e14-2-9.xhtml#A"', '"14.2.9-car.xhtml#A"').replace('"../css/book.css"', '"../../css/book.css"')


def test_build_map_on_fixture(tmp_path):
    def page(name, title, body=""):
        (tmp_path / name).write_text(f"<html><head><title>{title}</title></head><body>{body}</body></html>", encoding="utf-8")

    page("c14.xhtml", "14 Conses")
    page("cA.xhtml", "A Appendix")
    page("c26.xhtml", "26 Glossary")
    page("cover.xhtml", "Cover")
    page("s14-1.xhtml", "14.1 Cons Concepts")
    page("sA-1.xhtml", "A.1 Removed Features")
    page("e14-2-9.xhtml", "x",
         '<h3 id="d" class="entry"><span class="secno">14.2.9</span> <span class="names">car, cdr</span> '
         '<span class="kind">Accessor</span></h3>')
    page("e14-2-1.xhtml", "x",
         '<h3 id="d" class="entry"><span class="secno">14.2.1</span> <span class="names">&lt;=, &lt;</span> '
         '<span class="kind">Function</span></h3>')
    page("g-nonalph.xhtml", "Glossary")
    page("i-xyz.xhtml", "Index")
    m, specials = build_map(tmp_path)
    check_map(m, tmp_path)
    assert m["text/c14.xhtml"] == "text/14-conses/index.xhtml"
    assert m["text/cA.xhtml"] == "text/A-appendix/index.xhtml"
    assert m["text/s14-1.xhtml"] == "text/14-conses/14.1-cons-concepts.xhtml"
    assert m["text/sA-1.xhtml"] == "text/A-appendix/A.1-removed-features.xhtml"
    assert m["text/e14-2-9.xhtml"] == "text/14-conses/14.2.9-car.xhtml"
    assert m["text/e14-2-1.xhtml"] == "text/14-conses/14.2.1-lt-eq.xhtml"
    assert m["text/g-nonalph.xhtml"] == "text/26-glossary/nonalph.xhtml"
    assert m["text/i-xyz.xhtml"] == "text/index/xyz.xhtml"
    assert [s[1] for s in specials] == ["<="]
