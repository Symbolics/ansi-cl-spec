#!/usr/bin/env python3
"""Step 4: anchors for the CL symbols that have no entry heading, plus a C-index entry for compiler-macro.

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
    ("2-syntax/2.4-standard-macro-characters.xhtml", heading("SubSubSectio_Sharpsign_S_173"), ["structure"],
     "h4 2.4.8.13 Sharpsign S"),
    (DOC, r"<li>(?=<b>compiler-macro</b>)", ["compiler-macro"], "li of the doc-type list in the documentation entry"),
    (DOC, r"<li>(?=<b>variable</b>)", ["variable"], "li of the doc-type list in the documentation entry"),
]

INDEX_C = "index/c.xhtml"
INDEX_ANCHOR = '</p><p><b>compiler-macro-function</b>'
INDEX_NEW = ('</p><p><b>compiler-macro</b>  <a href="../25-environment/25.2.15-documentation.xhtml#'
             + name_to_fragment("compiler-macro") + '">documentation, (setf documentation)</a>.\n')


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


def add_index_entry(text):
    if "<b>compiler-macro</b>" in text:
        return text, 0
    if text.count(INDEX_ANCHOR) != 1:
        raise SystemExit("index/c.xhtml: anchor line not found exactly once")
    return text.replace(INDEX_ANCHOR, INDEX_NEW + INDEX_ANCHOR), 1


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
    new, k = add_index_entry(cache.get(INDEX_C) or (base / INDEX_C).read_bytes().decode("utf-8"))
    cache[INDEX_C] = new
    if k:
        print(f"  index entry compiler-macro: {INDEX_C}")
    if not a.check:
        for f, t in cache.items():
            (base / f).write_bytes(t.encode("utf-8"))
    print(f"04_remaining_anchors: {'would add' if a.check else 'added'} {n} anchors, {k} index entry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
