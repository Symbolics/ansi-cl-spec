"""Tests for tools/examples_extract.py and tools/examples_run.py."""
import shutil

import pytest

import examples_extract as ex
import examples_run as run

XHTML = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>t</title></head><body><section>
<h3 id="DictEntry_x_1" class="entry"><span class="secno">14.2.33</span> <span class="names">member, member-if</span> <span class="kind">Function</span></h3>
<dl><dt><b>Description:</b></dt><dd>blah</dd>
<dt><b>Examples:</b></dt><dd>
%s
</dd></dl></section></body></html>"""


def steps_of(pre_body):
    e = ex.extract_entry((XHTML % ("<pre>" + pre_body + "</pre>")).encode(), "e14-2-33.xhtml")
    return ex.finalize_unparsed(e)


def test_entry_metadata_and_simple_steps():
    e = steps_of(" (member 2 '(1 2 3)) → (2 3)\n (member 'e '(a b c d)) →  NIL\n")
    assert (e["secno"], e["names"], e["kind"]) == ("14.2.33", "member, member-if", "Function")
    s = e["steps"]
    assert [x["form_text"] for x in s] == ["(member 2 '(1 2 3))", "(member 'e '(a b c d))"]
    assert s[0]["expected_values"] == ["(2 3)"] and s[1]["expected_values"] == ["NIL"]


def test_multiline_form_and_multiple_values():
    e = steps_of(" (let ((x 1))\n   (values x\n           (/ 1 2))) → 1, 1/2\n")
    (s,) = e["steps"]
    assert s["form_text"].startswith("(let ((x 1))") and s["form_text"].endswith("(/ 1 2)))")
    assert s["expected_values"] == ["1", "1/2"]


def test_printed_output_and_result_on_later_lines():
    e = steps_of(" (let ((*print-gensym* nil))\n   (print (gensym)))\n▷ G6040 \n→ #:G6040\n")
    (s,) = e["steps"]
    assert s["expected_output"] == ["G6040 "] or s["expected_output"] == ["G6040"]
    assert s["expected_values"] == ["#:G6040"]


def test_no_values_and_markup_inside_pre():
    e = steps_of(" (values) → &lt; <i>no values</i> &gt;\n (eq 'a 'a) → <i><a href=\"g.xhtml#true\">true</a></i>\n"
                 " (foo <i>x</i>) → <b>1</b>\n")
    a, b, c = e["steps"]
    assert a["no_values"] is True and a["expected_values"] is None
    assert b["expected_values"] == ["true"] and b["expected_italics"] == [["true"]]
    assert c["expected_values"] == ["1"] and "italic-in-form" in c["flags"]


def test_no_expectation_or_alternatives_and_trailing_comma():
    e = steps_of(" (setq a 1)\n (f)\n→ 1\nOR→ 2\n (g) → (a),\n   (b)\n")
    a, f, g = e["steps"]
    assert a["expected_values"] is None and a["expected_output"] is None
    assert f["expected_values"] == ["1"] and f["alternatives"][0]["values"] == ["2"]
    assert g["expected_values"] == ["(a)", "(b)"]


def test_unparsed_items_recorded():
    e = steps_of(" Assuming x is special,\n (foo \"bar) → 1\n")
    reasons = {u["reason"] for u in e["unparsed"]}
    assert reasons == {"prose", "unbalanced form"} and e["steps"] == []


def test_trailing_prose_flags():
    e = steps_of(" (car 1) is an error.\n (a) ==(b) → 3\n")
    a, b = e["steps"]
    assert a["form_text"] == "(car 1)" and "expects-error" in a["flags"]
    assert b["form_text"] == "(a)" and b["expected_values"] == ["3"]


# ---------------------------------------------------------------- classification
def step(values=None, out=None, nov=False, italics=None, alts=(), flags=(), form="(f)"):
    return {"form_text": form, "expected_values": values,
            "expected_italics": italics if italics is not None else ([[] for _ in values] if values else None),
            "expected_output": out, "no_values": nov, "alternatives": list(alts), "flags": list(flags)}


def res(values=(), output=(), status="ok", no_values=False, error=None):
    return {"status": status, "values": list(values), "output": list(output),
            "no_values": no_values, "error": error}


@pytest.mark.parametrize("st,r,cls", [
    (step(["(2 3)"]), res(["(2 3)"]), "match"),
    (step(["(a  b)"]), res(["(A B)"]), "match"),                       # case/whitespace
    (step(["()"]), res(["NIL"]), "match"),
    (step(['"Ab"']), res(['"ab"']), "mismatch"),                       # strings are case-sensitive
    (step(["1", "2"]), res(["1"]), "mismatch"),
    (step(["3"]), res(["4"]), "mismatch"),
    (step(["#<FUNCTION F>"]), res(["#<FUNCTION F {1}>"]), "impl-dependent"),
    (step(["implementation-dependent"], italics=[["implementation-dependent"]]), res(["7"]), "impl-dependent"),
    (step(["true"], italics=[["true"]]), res(["T"]), "match"),
    (step(["true"], italics=[["true"]]), res(["NIL"]), "mismatch"),
    (step(["false"], italics=[["false"]]), res(["NIL"]), "match"),
    (step(["0.707107"]), res(["0.70710677"]), "impl-dependent"),
    (step(["1.0s0"]), res(["1.0"]), "impl-dependent"),
    (step(["0.5"]), res(["0.7"]), "mismatch"),
    (step(nov=True), res(no_values=True), "match"),
    (step(nov=True), res(["1"]), "mismatch"),
    (step(["1"], alts=[{"values": ["2"], "italics": [[]], "no_values": False}]), res(["2"]), "match"),
    (step(out=["hello  there"]), res(["NIL"], output=["", "HELLO there"]), "match"),
    (step(["NIL"], out=["a"]), res(["NIL"], output=["b"]), "mismatch"),
    (step(), res(["1"]), "no-expectation"),
    (step(["G12"], form="(gensym)"), res(["G99"]), "impl-dependent"),
    (step(["1"]), res(status="error", error="TYPE-ERROR x"), "error"),
    (step(["1"], flags=["expects-error"]), res(status="error", error="x"), "match"),
    (step(["1"]), res(status="started"), "timeout"),
    (step(["1"], flags=["italic-in-form"]), res(["1"]), "skipped"),
])
def test_classify(st, r, cls):
    assert run.classify(st, r)[0] == cls


def test_classify_skip_reason():
    assert run.classify(step(["1"]), None, "sleep")[0] == "skipped"


def test_parse_run_output():
    text = "STEP 0\nVAL 3\nEND 0\nSTEP 1\nOUT a\\nb\nERR SIMPLE-ERROR boom\nEND 1\nSTEP 2\n"
    r = run.parse_run_output(text, 4)
    assert r[0]["values"] == ["3"] and r[0]["status"] == "ok"
    assert r[1]["status"] == "error" and r[1]["output"] == ["a\nb"]
    assert r[2]["status"] == "started" and r[3]["status"] == "none"


def test_safety():
    mk = lambda f: [{"form_text": f}]
    assert run.safety_reasons(mk("(sleep 1)"))
    assert run.safety_reasons(mk('(open "/etc/passwd")'))
    assert run.safety_reasons(mk("(sb-ext:quit)"))
    assert run.safety_reasons(mk('(load "../x")'))
    assert not run.safety_reasons(mk('(with-open-file (s "data.in" :direction :output) 1)'))
    assert not run.safety_reasons(mk('(format t "~S ~&" 1)'))
    assert not run.safety_reasons(mk('(list \'sleepy "open")'))


@pytest.mark.skipif(shutil.which("sbcl") is None, reason="sbcl not installed")
def test_sbcl_round_trip():
    forms = ["(+ 1 2)", "(values)", "(progn (print 1) (floor 7 2))", "(car 1)", "(+ 1 2)"]
    results, timed_out = run.run_entry_sbcl(forms)
    assert not timed_out
    assert results[0]["values"] == ["3"]
    assert results[1]["no_values"] is True
    assert results[2]["values"] == ["3", "1"] and "1" in "".join(results[2]["output"])
    assert results[3]["status"] == "error"          # evaluation continues after an error
    assert results[4]["values"] == ["3"]
    st = step(["3"], form="(+ 1 2)")
    assert run.classify(st, results[0])[0] == "match"
