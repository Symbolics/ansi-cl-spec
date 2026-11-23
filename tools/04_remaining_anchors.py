#!/usr/bin/env python3
"""Step 4: anchors for the CL symbols that have no entry heading, plus index entries for them.

The doc-type symbols compiler-macro, structure and variable are anchored in the doc-type list of the
documentation entry (25.2.15); compiler-macro and variable get their own lowercase index entry (placed
immediately before a same-spelled capitalised kind-group heading, as the index does for class/Class),
and structure keeps its Sharpsign S link and gains a documentation link. A structure anchor placed
earlier on the Sharpsign S heading is removed (REMOVALS), so the symbol is anchored exactly once.

Each placement inserts empty <span id=".." data-symbol=".."></span> elements immediately inside the
start of a target element (found by a regex that must match exactly once). Idempotent;
--check prints each placement and writes nothing.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anchors import name_to_data_symbol, name_to_id, name_to_fragment  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / "src" / "OEBPS" / "text"


def heading(tag_id):
    return rf'<h\d id="{tag_id}"[^>]*>'


LL = "3-evaluation-and-compilation/3.4-lambda-lists.xhtml"
OPT = "3-evaluation-and-compilation/3.8.25-optimize.xhtml"
CASE = "5-data-and-control-flow/5.3.46-case.xhtml"
DOC = "25-environment/25.2.15-documentation.xhtml"

# (file, regex ending exactly at the insertion point, [symbols], description)
PLACEMENTS = [
    (LL, heading("SubSubSubSec_Suppressing__248"), ["&allow-other-keys"], "h5 3.4.1.4.1 Suppressing Keyword Argument Checking"),
    (LL, heading("SubSubSectio_Specifiers_f_250"), ["&aux"], "h4 3.4.1.5 Specifiers for &aux variables"),
    (LL, heading("SubSection_Macro_Lambda_254"), ["&body", "&environment", "&whole"], "h3 3.4.4 Macro Lambda Lists"),
    (LL, heading("SubSubSectio_Specifiers_f_247"), ["&key"], "h4 3.4.1.4 Specifiers for keyword parameters"),
    (LL, heading("SubSubSectio_Specifiers_f_245"), ["&optional"], "h4 3.4.1.2 Specifiers for optional parameters"),
    (LL, heading("SubSubSectio_A_specifier__246"), ["&rest"], "h4 3.4.1.3 A specifier for a rest parameter"),
    (OPT, r"<td>(?=<b>compilation-speed</b>)", ["compilation-speed"], "td in Figure 3-25 (optimize qualities)"),
    (OPT, r"<td>(?=<b>debug</b>)", ["debug"], "td in Figure 3-25 (optimize qualities)"),
    (OPT, r"<td>(?=<b>safety</b>)", ["safety"], "td in Figure 3-25 (optimize qualities)"),
    (OPT, r"<td>(?=<b>space</b>)", ["space"], "td in Figure 3-25 (optimize qualities)"),
    (OPT, r"<td>(?=<b>speed</b>)", ["speed"], "td in Figure 3-25 (optimize qualities)"),
    (CASE, r"<p>(?=\s*otherwise-clause::=)", ["otherwise"], "p holding the otherwise-clause syntax in the case entry"),
    ("7-objects/7.6-generic-functions-and-methods.xhtml", heading("SubSubSectio_Standard_Met_552"), ["standard"],
     "h4 7.6.6.2 Standard Method Combination"),
    (DOC, r"<li>(?=<b>compiler-macro</b>)", ["compiler-macro"], "li of the doc-type list in the documentation entry"),
    (DOC, r"<li>(?=<b>structure</b>)", ["structure"], "li of the doc-type list in the documentation entry"),
    (DOC, r"<li>(?=<b>variable</b>)", ["variable"], "li of the doc-type list in the documentation entry"),
]

# anchors an earlier version of this step placed elsewhere: (file, exact span text) removed if present
REMOVALS = [
    ("2-syntax/2.4-standard-macro-characters.xhtml", '<span id="structure" data-symbol="structure"></span>'),
]

INDEX_C = "index/c.xhtml"
INDEX_V = "index/v.xhtml"
INDEX_S = "index/s.xhtml"
# (index file, name, line that the new entry is inserted before)
INDEX_ENTRIES = [
    (INDEX_C, "compiler-macro", "</p><p><b>compiler-macro-function</b>"),
    (INDEX_V, "variable", "</p><p><b>Variable</b>"),  # before the kind-group heading, like class/Class
]
DOC_LINK = '<a href="../25-environment/25.2.15-documentation.xhtml#{}">documentation, (setf documentation)</a>'
# the structure entry: existing Sharpsign S link (original section anchor), then the documentation link
STRUCT_OLD = ('<p><b>structure</b>  <a href="../2-syntax/2.4-standard-macro-characters.xhtml'
              '#SubSubSectio_Sharpsign_S_173">Sharpsign S</a>.\n')
STRUCT_NEW = ('<p><b>structure</b>  <a href="../2-syntax/2.4-standard-macro-characters.xhtml'
              '#SubSubSectio_Sharpsign_S_173">Sharpsign S</a>, \n'
              + DOC_LINK.format(name_to_fragment("structure")) + '.\n')


def span(sym):
    return f'<span id="{name_to_id(sym)}" data-symbol="{name_to_data_symbol(sym)}"></span>'


def place(text, regex, syms, label):
    """Insert spans for SYMS at the single match of REGEX; skip symbols already present."""
    todo = [s for s in syms if f'<span id="{name_to_id(s)}" data-symbol=' not in text]
    if not todo:
        return text, 0
    if len(todo) != len(syms):
        raise SystemExit(f"{label}: only some of {syms} already present")
    ms = list(re.finditer(regex, text))
    if len(ms) != 1:
        raise SystemExit(f"{label}: pattern {regex!r} matched {len(ms)} times, expected 1")
    at = ms[0].end()
    return text[:at] + "".join(span(s) for s in syms) + text[at:], len(syms)


def add_index_entry(text, name, anchor):
    """Insert a documentation-link entry for NAME immediately before ANCHOR (must occur once)."""
    if f"<b>{name}</b>" in text:
        return text, 0
    if text.count(anchor) != 1:
        raise SystemExit(f"index entry {name}: anchor {anchor!r} not found exactly once")
    new = f"</p><p><b>{name}</b>  " + DOC_LINK.format(name_to_fragment(name)) + ".\n"
    return text.replace(anchor, new + anchor), 1


def add_structure_link(text):
    """Add the documentation link after the Sharpsign S link in the structure entry (index/s.xhtml)."""
    if "<p><b>structure</b>  " + '<a href="../2-syntax/2.4-standard-macro-characters.xhtml#SubSubSectio_Sharpsign_S_173">Sharpsign S</a>, \n' in text:
        return text, 0
    # a tree already repointed by an earlier version of step 5 has #structure on the Sharpsign S link
    text = text.replace(STRUCT_OLD.replace("#SubSubSectio_Sharpsign_S_173", "#structure"), STRUCT_OLD)
    if text.count(STRUCT_OLD) != 1:
        raise SystemExit("index/s.xhtml: structure entry not found in its expected form")
    return text.replace(STRUCT_OLD, STRUCT_NEW), 1


def remove_span(text, span_text):
    return (text.replace(span_text, "", 1), 1) if span_text in text else (text, 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="dry run")
    ap.add_argument("--text-dir", default=str(TEXT))
    a = ap.parse_args(argv)
    base = Path(a.text_dir)
    cache = {}
    n = 0
    for f, regex, syms, desc in PLACEMENTS:
        text = cache.get(f) or (base / f).read_bytes().decode("utf-8")
        new, k = place(text, regex, syms, f)
        cache[f] = new
        if k:
            n += k
            print(f"  {', '.join(syms)}: {f}  [{desc}]")
    for f, span_text in REMOVALS:
        cache[f], k = remove_span(cache.get(f) or (base / f).read_bytes().decode("utf-8"), span_text)
        if k:
            print(f"  removed {span_text}: {f}")
    k = 0
    for f, name, anchor in INDEX_ENTRIES:
        cache[f], kk = add_index_entry(cache.get(f) or (base / f).read_bytes().decode("utf-8"), name, anchor)
        if kk:
            print(f"  index entry {name}: {f}")
        k += kk
    cache[INDEX_S], kk = add_structure_link(cache.get(INDEX_S) or (base / INDEX_S).read_bytes().decode("utf-8"))
    if kk:
        print(f"  index entry structure: documentation link added in {INDEX_S}")
    k += kk
    if not a.check:
        for f, t in cache.items():
            (base / f).write_bytes(t.encode("utf-8"))
    print(f"04_remaining_anchors: {'would add' if a.check else 'added'} {n} anchors, {k} index changes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
