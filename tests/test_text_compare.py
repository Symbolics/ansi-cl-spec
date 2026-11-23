"""Tests for the TeX entry parser, the TeX->text normaliser and the comparator
(fixture strings only; no network, no vendor/ tree needed)."""
import textwrap

import compare_text
import epub_entries
import tex_entries
import tex_to_text as T

DEFS = T.parse_defs(textwrap.dedent(r"""
    \def\oftype #1{of \term{type} \typeref{#1}}
    \def\Thefunction #1{The \term{function} \funref{#1}}
    \def\Lazychecktype#1#2{Should be prepared to signal an error \oftype{type-error}
         if \param{#1} is not #2.}
    \def\TraversalRules{Section 3.6 (Traversal Rules and Side Effects)}
    \def\Conditions{Chapter 9 (Conditions)}
    """))


def tt(s, defs=DEFS, stats=None):
    return T.tex_to_text(s, defs, stats)


# ---------------------------------------------------------------- normaliser

def test_inline_macros():
    assert tt(r"\funref{car} of a \term{list}, see \param{x} and \kwd{test}.") == \
        "car of a list, see x and :test."


def test_nil_t_and_lambda_keywords():
    assert tt(r"\nil\ is \misc{t}; {\key} {\opt} {\rest}") == "nil is t; &key &optional &rest"


def test_dashes_and_quotes():
    assert tt(r"item---an ``object''") == 'item\u2014an "object"'


def test_issue_markers_dropped_but_content_kept():
    assert tt(r"\issue{FOO:BAR}Kept text.\endissue{FOO:BAR}") == "Kept text."


def test_sentence_macros_expand_from_defs():
    assert tt(r"\Thefunction{member} is deprecated.") == "The function member is deprecated."
    assert tt(r"\Lazychecktype{list}{a \term{proper list}}") == \
        "Should be prepared to signal an error of type type-error if list is not a proper list."


def test_section_references():
    assert tt(r"\secref\TraversalRules") == "Section \u00a7"
    assert tt(r"{\secref\Conditions}") == "Chapter \u00a7"
    assert tt(r"\seesection\TraversalRules") == "see Section \u00a7"


def test_code_block_arrows_and_literals():
    src = "\\code\n (f 1) \\EV 2\n (format t \"~&x~%\")  ; a -- b $ c\n\\endcode"
    out = tt(src)
    assert "(f 1) \u2192 2" in out
    assert '~&x~%' in out and "a--b $ c" in out  # literal ~ % $ (dashes folded by normalize_text)


def test_code_double_backslash_is_one_backslash():
    assert tt("\\code\n #\\\\Space\n\\endcode") == "#\\Space"


def test_defun_with_values():
    assert tt(r"\DefunWithValues member {item list {\key} key test} {tail}") == \
        "member item list &key key test \u2192 tail"


def test_multi_entry_table():
    src = r"\DefunMultiWithValues {x} {y} {\entry{a} \entry{b}}"
    assert T.Renderer(DEFS).render(src).split() == "a x \u2192 y b x \u2192 y".split()
    assert T.Renderer(DEFS).render(src).strip().count("\n") == 1  # one line per entry


def test_unknown_macro_keeps_argument_and_is_counted():
    from collections import Counter
    st = Counter()
    assert tt(r"\frobnicate{keep me}", stats=st) == "keep me"
    assert st["\\frobnicate"] == 1


def test_math_and_ties():
    assert tt(r"and~$\pi$ is $x^2$") == "and \u03c0 is x2"


def test_normalize_text_folds_dashes_and_quotes():
    assert T.normalize_text("a \u2013 b \u201cq\u201d \u00a0 c") == 'a--b "q" c'


def test_def_inside_text_defines_macro():
    assert tt(r"\def\Result#1{[#1]}\Result{x}") == "[x]"


# ------------------------------------------------------------ entry parsing

DICT = textwrap.dedent(r"""
    % comment-only line
    \def\realtypespec#1{
    \label Compound Type Specifier Kind::
    Abbreviating #1.
    }
    % \begincom{commented-out}\ftype{Function}
    \begincom{member, member-if,
              member-if-not}\ftype{function}

    \label Syntax::
    \DefunWithValues member {item list} {tail}

    \label Description::
    Searches. % trailing comment
    \label Side Effects:\None.
    Stray text after an empty label.

    \label Affected By:\None!

    \label Examples::
    \code
     (member 1 '(1)) \EV (1)
    % a commented line inside code
    \endcode
    \endcom%{member}

    \begincom{real}\ftype{System Class}
    \label Description::
    A real.
    \realtypespec{real}
    \endcom
    """)


def test_parse_dict_text_entries_and_kinds():
    es = tex_entries.parse_dict_text(DICT, "dict-x.tex", 14)
    assert [e["names"] for e in es] == [["member", "member-if", "member-if-not"], ["real"]]
    assert es[0]["kind"] == "Function"  # lowercase \ftype normalised
    assert es[0]["chapter"] == 14


def test_sections_empty_labels_and_text_attachment():
    e = tex_entries.parse_dict_text(DICT, "dict-x.tex", 14)[0]
    labels = [(s["label"], s["empty"]) for s in e["sections"]]
    assert labels == [("Syntax", False), ("Description", False), ("Side Effects", True),
                      ("Affected By", True), ("Examples", False)]
    desc = [s for s in e["sections"] if s["label"] == "Description"][0]
    assert "trailing comment" not in desc["raw"]
    assert "Stray text after an empty label." in desc["raw"]  # continues previous section


def test_comment_inside_code_only_at_line_start():
    e = tex_entries.parse_dict_text(DICT, "dict-x.tex", 14)[0]
    ex = [s for s in e["sections"] if s["label"] == "Examples"][0]["raw"]
    assert "a commented line" not in ex and "(member 1" in ex


def test_label_macro_expansion():
    e = tex_entries.parse_dict_text(DICT, "dict-x.tex", 14)[1]
    assert [s["label"] for s in e["sections"]] == ["Description", "Compound Type Specifier Kind"]


def test_percent_escape_kept_in_prose():
    assert "100\\%" in tex_entries.strip_comments("100\\% sure % comment")


# -------------------------------------------------------------- EPUB parsing

EPUB = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><section>
<h3 id="DictEntry_x" class="entry"><span class="secno">14.2.33</span> <span class="names">member, member-if</span> <span class="kind">Function</span></h3>
<dl>
<dt><b>Syntax:</b></dt><dd><b>member</b> <i>item list <code>&amp;key</code> key</i> \u2192 <i>tail</i></dd>
<dt><b>Description:</b></dt><dd>See <i><a href="g-p.xhtml#x">proper list</a></i>. Section <a href="s3-6.xhtml#s">3.6 Traversal</a>.
<p>Second.</p></dd>
<dt><b>Examples:</b></dt><dd><pre> (member 1 '(1)) \u2192 (1)
 (f)
</pre></dd>
</dl></section></body></html>"""


def test_epub_entry_parse(tmp_path):
    f = tmp_path / "e14-2-33.xhtml"
    f.write_text(EPUB, encoding="utf-8")
    e = epub_entries.parse_file(f)
    assert (e["secno"], e["names"], e["kind"]) == ("14.2.33", ["member", "member-if"], "Function")
    assert e["chapter"] == 14
    assert [s["label"] for s in e["sections"]] == ["Syntax", "Description", "Examples"]
    assert e["sections"][0]["text"] == "member &key key \u2192 tail".replace("member &key", "member item list &key")
    assert "Section \u00a7." in e["sections"][1]["text"]  # section link text replaced by the marker
    assert e["sections"][2]["text"].splitlines() == ["(member 1 '(1)) \u2192 (1)", " (f)"]  # lines kept


# ------------------------------------------------------------------ compare

def test_tokens_and_diff_ops():
    assert compare_text.tokens("a, b::=c==d (x)") == ["a", ",", "b", "::=", "c", "==", "d", "(", "x", ")"]
    ratio, ops, n = compare_text.diff_ops(["a", "b", "c"], ["a", "x", "c"])
    assert 0.6 < ratio < 0.7 and n == 1 and ops[0]["tex"] == "b" and ops[0]["epub"] == "x"
    assert compare_text.diff_ops(["a"], ["a"])[0] == 1.0


def test_match_by_chapter_names_kind():
    t = [{"chapter": 4, "names": ["list"], "kind": "System Class"},
         {"chapter": 14, "names": ["list"], "kind": "Function"}]
    e = [{"chapter": 14, "names": ["list"], "kind": "Function"},
         {"chapter": 4, "names": ["list"], "kind": "System Class"},
         {"chapter": 5, "names": ["zzz"], "kind": "Macro"}]
    pairs, tex_only, epub_only, how = compare_text.match(t, e)
    assert sorted(pairs) == [(0, 1), (1, 0)] and tex_only == [] and epub_only == [2]


NEW_LAYOUT = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><section>
<h3 id="DictEntry_x" class="entry" data-kind="function"><span class="secno">14.2.33</span> <span class="names"><span id="member" data-symbol="member">member</span>, <span id="member-if" data-symbol="member-if">member-if</span></span> <span class="kind">Function</span></h3>
<dl>
<dt data-section="description"><b>Description:</b></dt><dd>See <i><a href="../26-glossary/p.xhtml#x">proper list</a></i>. Section <a href="../3-evaluation-and-compilation/3.6-traversal.xhtml#s">3.6 Traversal</a>, <a href="index.xhtml#c">14 Conses</a>.</dd>
<dt data-section="examples"><b>Examples:</b></dt><dd><pre> (member 1 '(1)) → (1)
</pre></dd>
</dl></section></body></html>"""


def test_epub_tree_new_layout_found_by_markup(tmp_path):
    text = tmp_path / "OEBPS" / "text"
    (text / "14-conses").mkdir(parents=True)
    (text / "index").mkdir()
    (text / "14-conses" / "14.2.33-member.xhtml").write_text(NEW_LAYOUT, encoding="utf-8")
    (text / "14-conses" / "index.xhtml").write_text("<html xmlns='http://www.w3.org/1999/xhtml'><body/></html>")
    (text / "index" / "m.xhtml").write_text("<html xmlns='http://www.w3.org/1999/xhtml'><body/></html>")
    (es,) = epub_entries.parse_tree(text)
    assert (es["secno"], es["names"], es["kind"]) == ("14.2.33", ["member", "member-if"], "Function")
    assert es["file"] == "text/14-conses/14.2.33-member.xhtml"  # relative to OEBPS/
    assert [s["label"] for s in es["sections"]] == ["Description", "Examples"]
    assert es["sections"][0]["text"].count("§") == 2 and "proper list" in es["sections"][0]["text"]
    import examples_extract
    (xe,) = examples_extract.extract_all(text)
    assert (xe["secno"], xe["names"], xe["file"]) == ("14.2.33", "member, member-if", es["file"])
    assert len(xe["steps"]) == 1


def test_epub_tree_original_layout(tmp_path):
    text = tmp_path / "OEBPS" / "text"
    text.mkdir(parents=True)
    (text / "e14-2-33.xhtml").write_text(EPUB, encoding="utf-8")
    (text / "c14.xhtml").write_text("<html xmlns='http://www.w3.org/1999/xhtml'><body/></html>")
    (es,) = epub_entries.parse_tree(text)
    assert es["file"] == "text/e14-2-33.xhtml" and es["secno"] == "14.2.33"
    assert "Section §." in es["sections"][1]["text"]
