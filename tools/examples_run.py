#!/usr/bin/env python3
"""Evaluate extracted examples in SBCL (one fresh process per entry) and classify.

Classes: match, mismatch, error, impl-dependent, no-expectation, skipped,
timeout, unparsed.  Results are keyed by section number + names.
"""
import argparse
import json
import os
import re
import resource
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import examples_extract as ex  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LISP = ROOT / "tools/lisp/run-example.lisp"
TIMEOUT = 15

# ---------------------------------------------------------------- safety
# Any hit here -> whole entry skipped.
HARD = ["ed", "sleep", "room", "run-program", "quit", "exit", "dribble",
        "require", "shell", "sb-[\\w-]*"]
# Allowed only on relative paths (they act inside the temp cwd).
FILEOPS = ["delete-file", "rename-file", "open", "with-open-file", "load",
           "compile-file", "directory", "ensure-directories-exist", "probe-file"]
STR_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')


def strip_strings_comments(form):
    form = re.sub(r"#\\.", "", form)
    form = STR_RE.sub('""', form)
    return re.sub(r";[^\n]*", "", form)


def token_re(names):
    return re.compile(r"(?<![\w*+-])(?:" + "|".join(names) + r")(?![\w*+-])", re.I)


HARD_RE, FILE_RE = token_re(HARD), token_re(FILEOPS)
SB_PREFIX = re.compile(r"\bsb-[\w-]*:", re.I)


def abs_path_literal(s):
    # "~/" and "~user/" are home-relative paths; "~S", "~%" ... are FORMAT directives
    return bool(re.match(r"^\s*(/|~/|~[\w-]+/)", s) or ":\\" in s or ".." in s.split("/"))


def safety_reasons(steps):
    """Return list of reasons the entry must be skipped (empty -> safe)."""
    reasons = []
    for st in steps:
        form = st["form_text"]
        bare = strip_strings_comments(form)
        for m in HARD_RE.finditer(bare):
            reasons.append(f"{m.group(0)} in `{form[:40]}`")
        if SB_PREFIX.search(form):
            reasons.append(f"sb- package reference in `{form[:40]}`")
        for lit in STR_RE.findall(form):
            if abs_path_literal(lit):
                reasons.append(f"absolute/parent path literal {lit!r}")
        if "\\" in "".join(STR_RE.findall(form)) and ":\\" in form:
            reasons.append("windows path literal")
    return sorted(set(reasons))


# ------------------------------------------------------------ run SBCL
def unesc(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            out.append({"n": "\n", "r": "\r", "\\": "\\"}.get(n, n))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def lisp_string(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_run_output(text, n):
    """Parse harness output into n result dicts (status ok/error/timeout/none)."""
    res = [{"status": "none", "values": [], "output": [], "error": None} for _ in range(n)]
    cur = None
    for line in text.split("\n"):
        tag, _, rest = line.partition(" ")
        if tag == "STEP":
            try:
                cur = res[int(rest)]
            except (ValueError, IndexError):
                cur = None
            if cur is not None:
                cur["status"] = "started"
        elif cur is None:
            continue
        elif tag == "OUT":
            cur["output"].append(unesc(rest))
        elif tag == "VAL":
            cur["values"].append(unesc(rest))
        elif tag == "NOVALUES":
            cur["no_values"] = True
        elif tag == "ERR":
            cur["error"] = unesc(rest)
            cur["status"] = "error"
        elif tag == "TIMEOUT":
            cur["status"] = "timeout"
        elif tag == "END":
            if cur["status"] == "started":
                cur["status"] = "ok"
            cur = None
    return res


def run_entry_sbcl(forms, timeout=TIMEOUT):
    """Run forms in a fresh SBCL; return (results, process_timed_out)."""
    with tempfile.TemporaryDirectory(prefix="exin-") as indir, \
            tempfile.TemporaryDirectory(prefix="exwd-") as wd:
        inp = Path(indir) / "steps.in"
        inp.write_text(" ".join(lisp_string(f) for f in forms), encoding="utf-8")
        env = {"PATH": os.environ.get("PATH", ""), "HOME": wd,
               "LC_ALL": "C.UTF-8", "TMPDIR": wd}

        def limits():
            resource.setrlimit(resource.RLIMIT_FSIZE, (50_000_000, 50_000_000))

        timed_out = False
        try:
            p = subprocess.run(
                ["sbcl", "--dynamic-space-size", "1GB", "--script", str(LISP), str(inp)],
                cwd=wd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, timeout=timeout, preexec_fn=limits)
            out = p.stdout
        except subprocess.TimeoutExpired as e:
            timed_out = True
            out = e.stdout or b""
        return parse_run_output(out.decode("utf-8", "replace"), len(forms)), timed_out


# ------------------------------------------------------- classification
def norm(s):
    """Normalise whitespace; lower-case outside string literals and #\\ chars."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 2 if s[j] == "\\" else 1
            out.append(s[i:j + 1])
            i = j + 1
        elif s.startswith("#\\", i):
            m = re.match(r"#\\(?:[A-Za-z0-9_-]{2,}|.)", s[i:])
            tok = m.group(0)
            out.append("#\\space" if tok == "#\\ " else (tok.lower() if len(tok) > 3 else tok))   # SBCL prints #\Space as #\<space>
            i += len(tok)
        else:
            out.append(c.lower())
            i += 1
    t = re.sub(r"\s+", " ", "".join(out)).strip()
    t = re.sub(r"\( ", "(", t)
    t = re.sub(r" \)", ")", t)
    t = re.sub(r"(?<![\w\"])\(\)", "nil", t)       # () and NIL are the same object
    return t


IMPL_RE = re.compile(r"#<|#:G?\w*\d+|implementation[- ]dependent|\.\.\.|approximately|at least", re.I)
IMPL_FORM_RE = re.compile(r"(?<![\w-])(gensym|gentemp|random|make-random-state)(?![\w-])", re.I)
FLOAT_RE = re.compile(r"(?<![\w.+-])[-+]?(?:\d+\.\d*|\.\d+|\d+(?=[esfdl][-+]?\d))(?:[esfdl][-+]?\d+)?(?![\w.])", re.I)


def float_equiv(a, b):
    """True when a and b differ only in float digits/format (s0, L0, 7 vs 9 digits)."""
    fa, fb = FLOAT_RE.findall(a), FLOAT_RE.findall(b)
    if not fa or len(fa) != len(fb):
        return False
    if FLOAT_RE.sub("#", a) != FLOAT_RE.sub("#", b):
        return False
    try:
        for x, y in zip(fa, fb):
            x, y = float(re.sub("[sfdlSFDL]", "e", x)), float(re.sub("[sfdlSFDL]", "e", y))
            if abs(x - y) > 1e-4 * max(abs(x), abs(y), 1e-30):
                return False
    except ValueError:
        return False
    return True


def value_class(expected, italics, actual):
    """Classify one expected value text against the actual printed value."""
    spans = [x.strip() for x in italics]
    whole = len(spans) == 1 and norm(spans[0]) == norm(expected)
    if whole and norm(expected) == "true":
        return "match" if norm(actual) != "nil" else "mismatch"
    if whole and norm(expected) == "false":
        return "match" if norm(actual) == "nil" else "mismatch"
    if norm(expected) == norm(actual):
        return "match"
    if float_equiv(norm(expected), norm(actual)):
        return "impl-dependent"
    if spans or IMPL_RE.search(expected):
        return "impl-dependent"
    return "mismatch"


RANK = {"match": 0, "impl-dependent": 1, "mismatch": 2}


def worst(classes):
    return max(classes, key=lambda c: RANK[c]) if classes else "match"


def compare_values(exp_vals, italics, no_values, res):
    actual = [] if res.get("no_values") else res["values"]
    if no_values:
        return "match" if not actual else "mismatch"
    if len(exp_vals) != len(actual):
        if any(IMPL_RE.search(v) for v in exp_vals) or any(italics):
            return "impl-dependent"
        return "mismatch"
    return worst([value_class(e, it, a) for e, it, a in zip(exp_vals, italics, actual)])


def compare_output(exp_lines, res):
    exp = norm("\n".join(exp_lines))
    act = norm("\n".join(res["output"]))
    if exp == act:
        return "match"
    if IMPL_RE.search("\n".join(exp_lines)):
        return "impl-dependent"
    return "mismatch"


def classify(step, res, skip_reason=None):
    """-> (class, detail-dict).  `res` is a parse_run_output result dict."""
    if skip_reason:
        return "skipped", {"reason": skip_reason}
    if "italic-in-form" in step["flags"]:
        return "skipped", {"reason": "metavariable (italic) inside form"}
    if "ellipsis-in-form" in step["flags"]:
        return "skipped", {"reason": "elided code (...) inside form"}
    if res["status"] == "timeout":
        return "timeout", {}
    if res["status"] == "error":
        if "expects-error" in step["flags"]:
            return "match", {"reason": "book says this is an error", "error": res["error"]}
        return "error", {"error": res["error"]}
    if res["status"] == "terminated":
        return "error", {"error": "process terminated during this step (debugger/abort/exit)"}
    if res["status"] == "unreached":
        return "skipped", {"reason": "not reached: an earlier step terminated the process"}
    if res["status"] in ("none", "started"):
        return "timeout", {"reason": "no result (process timed out)"}
    has_exp = step["expected_values"] is not None or step["no_values"] \
        or step["expected_output"] is not None
    if not has_exp:
        return "no-expectation", {}
    options = [(step["expected_values"], step["expected_italics"], step["no_values"])]
    for a in step.get("alternatives", []):
        options.append((a["values"], a["italics"], a["no_values"]))
    if IMPL_FORM_RE.search(strip_strings_comments(step["form_text"])):
        step = dict(step, _impl_form=True)
    results = []
    for vals, its, nov in options:
        parts = []
        if vals is not None or nov:
            parts.append(compare_values(vals or [], its or [], nov, res))
        if step["expected_output"] is not None:
            parts.append(compare_output(step["expected_output"], res))
        results.append(worst(parts))
    best = min(results, key=lambda c: RANK[c])
    if best == "mismatch" and step.get("_impl_form"):
        best = "impl-dependent"
        return best, {"reason": "form uses gensym/gentemp/random"}
    return best, {}


# ------------------------------------------------------------- driver
def run_one(entry):
    steps = entry["steps"]
    reasons = safety_reasons(steps)
    skip_flags = {"italic-in-form", "ellipsis-in-form"}
    forms = ["nil" if skip_flags & set(s["flags"]) else s["form_text"] for s in steps]
    if reasons:
        results, timed_out = [None] * len(steps), False
    else:
        results, timed_out = run_entry_sbcl(forms)
    if not timed_out and not reasons:
        for r in results:
            if r["status"] == "started":
                r["status"] = "terminated"
            elif r["status"] == "none":
                r["status"] = "unreached"
    out = []
    for s, r in zip(steps, results):
        cls, detail = classify(s, r, "; ".join(reasons)[:300] if reasons else None)
        rec = dict(s)
        rec["class"] = cls
        rec["actual_values"] = None if r is None or r.get("no_values") else r["values"]
        rec["actual_no_values"] = bool(r and r.get("no_values"))
        rec["actual_output"] = None if r is None else r["output"]
        rec["detail"] = detail
        out.append(rec)
    return {"secno": entry["secno"], "names": entry["names"], "kind": entry["kind"],
            "file": entry["file"], "skipped_reasons": reasons,
            "process_timed_out": timed_out, "steps": out,
            "unparsed": entry["unparsed"]}


def sort_key(e):
    return [int(x) if x.isdigit() else x for x in e["secno"].split(".")]


def run_all(entries, jobs=8):
    with ThreadPoolExecutor(jobs) as pool:
        res = list(pool.map(run_one, entries))
    return sorted(res, key=sort_key)


def trunc(s, n=70):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n - 1] + "…"


def cell(s, n=70):
    return trunc(s, n).replace("|", "\\|").replace("`", "'")


def fmt_exp(st):
    p = []
    if st["no_values"]:
        p.append("<no values>")
    if st["expected_values"] is not None:
        p.append(", ".join(st["expected_values"]))
    if st["expected_output"]:
        p.append("▷ " + " / ".join(st["expected_output"]))
    return " ".join(p)


def fmt_act(st):
    p = []
    if st["detail"].get("error"):
        return "ERROR " + st["detail"]["error"]
    if st["actual_no_values"]:
        p.append("<no values>")
    elif st["actual_values"] is not None:
        p.append(", ".join(st["actual_values"]))
    if st["actual_output"]:
        p.append("▷ " + " / ".join(st["actual_output"]))
    return " ".join(p)


def write_summary(results, path):
    steps = [s for e in results for s in e["steps"]]
    unparsed = [u for e in results for u in e["unparsed"]]
    classes = Counter(s["class"] for s in steps)
    classes["unparsed"] += len(unparsed)
    order = ["match", "mismatch", "error", "impl-dependent", "no-expectation",
             "skipped", "timeout", "unparsed"]
    L = ["# Example audit summary", "",
         f"Entries with examples: {len(results)}; evaluable steps: {len(steps)}; "
         f"unparsed items: {len(unparsed)}.", "",
         "Generated by `tools/examples_extract.py` + `tools/examples_run.py` (SBCL, one fresh "
         "process per entry). Mismatches are candidates for human review, not verdicts.", "",
         "Harness notes: entries are keyed by section number and names. `impl-dependent` covers `#<...>`, "
         "italic placeholders, gensym/gentemp/random forms, and float digit/format differences (rel. tol. 1e-4). "
         "Notation equivalences applied: whitespace, case outside strings, `()` = `NIL`, `#\\Space` = `#\\ `. "
         "An entry-level safety pre-scan skips entries using sleep/exit/require/absolute paths etc. "
         "A step whose prose says \"is an error\"/\"should signal an error\" counts as `match` if it errors. "
         "Steps with italic metavariables or `...` elisions are `skipped`. SBCL specifics (package locks on "
         "CL symbols, locked standard readtable, no interactive stdin/debugger) produce `error`s that are "
         "implementation artefacts, not book bugs.", "",
         "## Counts per class", "", "| class | steps |", "|---|---|"]
    L += [f"| {c} | {classes.get(c, 0)} |" for c in order]
    L += ["", "## Per chapter", "", "| chapter | " + " | ".join(order) + " |",
          "|---|" + "---|" * len(order)]
    per = defaultdict(Counter)
    for e in results:
        ch = e["secno"].split(".")[0]
        for s in e["steps"]:
            per[ch][s["class"]] += 1
        per[ch]["unparsed"] += len(e["unparsed"])
    for ch in sorted(per, key=int):
        L.append(f"| {ch} | " + " | ".join(str(per[ch].get(c, 0)) for c in order) + " |")

    def table(title, cls):
        rows = [(e, s) for e in results for s in e["steps"] if s["class"] == cls]
        L.extend(["", f"## {title} ({len(rows)})", "",
                  "| secno | names | blk:line | form | expected | actual |", "|---|---|---|---|---|---|"])
        for e, s in rows:
            L.append(f"| {e['secno']} | {cell(e['names'], 30)} | {s['block']}:{s['line']} | "
                     f"`{cell(s['form_text'], 60)}` | {cell(fmt_exp(s), 50)} | {cell(fmt_act(s), 60)} |")

    table("Mismatches", "mismatch")
    table("Errors", "error")
    table("Timeouts", "timeout")
    L.extend(["", f"## Unparsed items ({len(unparsed)})", "", "| secno | names | blk:line | reason | text |",
              "|---|---|---|---|---|"])
    for u in unparsed:
        L.append(f"| {u['secno']} | {cell(u['names'], 30)} | {u['block']}:{u['line']} | "
                 f"{u['reason']} | `{cell(u['text'], 70)}` |")
    sk = [e for e in results if e["skipped_reasons"]]
    L.extend(["", f"## Skipped entries ({len(sk)}) — for human review", "",
              "| secno | names | reason |", "|---|---|---|"])
    for e in sk:
        L.append(f"| {e['secno']} | {cell(e['names'], 30)} | {cell('; '.join(e['skipped_reasons']), 140)} |")
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
    return classes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--text-dir", default=str(ROOT / "src/OEBPS/text"))
    ap.add_argument("--out-dir", default=str(ROOT / "audit/examples"))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--only", help="comma-separated section numbers")
    a = ap.parse_args(argv)
    entries = ex.extract_all(a.text_dir)
    if a.only:
        want = set(a.only.split(","))
        entries = [e for e in entries if e["secno"] in want]
    results = run_all(entries, a.jobs)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "findings.json").write_text(
        json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    classes = write_summary(results, out / "summary.md")
    print(dict(classes))


if __name__ == "__main__":
    main()
