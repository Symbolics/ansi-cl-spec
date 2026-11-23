#!/usr/bin/env python3
"""Extract the Examples blocks of every dictionary entry into evaluable steps.

Each step: {secno, names, kind, file, block, line, form_text, expected_values,
expected_output, no_values, alternatives, expected_italics, flags}.
Anything that cannot be parsed goes into the entry's `unparsed` list.

Italic markup inside <pre> is kept as \\x01...\\x02 markers during parsing so
that placeholders such as <i>implementation-dependent</i> or <i>true</i> can
be told from literal text; the markers are stripped from the stored strings
(`expected_italics` keeps the italic spans).
"""
import argparse
import json
import re
import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epub_entries  # noqa: E402

IT0, IT1 = "\x01", "\x02"
ARROW, PRINT = "→", "▷"
NO_VALUES_RE = re.compile(r"^<\s*no values\s*>$", re.I)


def pre_text(pre):
    """Text content of a <pre>, italic spans wrapped in IT0/IT1."""
    out = []

    def walk(el):
        if el.text:
            out.append(el.text)
        for ch in el:
            if not isinstance(ch.tag, str):
                pass
            elif ch.tag.endswith("}i") or ch.tag == "i":
                out.append(IT0)
                walk(ch)
                out.append(IT1)
            else:
                walk(ch)
            if ch.tail:
                out.append(ch.tail)

    walk(pre)
    return "".join(out)


def clean(s):
    return s.replace(IT0, "").replace(IT1, "")


def scan(text, comments=True):
    """Return (depth, open_string, arrow_pos) for Lisp-ish text.

    arrow_pos is the index of the first ARROW outside strings/comments."""
    depth = 0
    i, n = 0, len(text)
    in_str = False
    arrow = None
    block = 0
    while i < n:
        c = text[i]
        if block:
            if text.startswith("|#", i):
                block -= 1
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif text.startswith("#|", i) and comments:
            block += 1
            i += 2
            continue
        elif text.startswith("#\\", i):
            i += 3
            continue
        elif c == "|" and comments:
            j = text.find("|", i + 1)
            if j < 0:
                break
            i = j + 1
            continue
        elif c == ";" and comments:
            j = text.find("\n", i)
            if j < 0:
                break
            i = j
            continue
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == ARROW and arrow is None:
            arrow = i
        i += 1
    return depth, in_str or bool(block), arrow


def split_values(text):
    """Split an expected-value string at top-level commas."""
    vals, cur, depth, in_str = [], [], 0, False
    i = 0
    while i < len(text):
        c = text[i]
        if in_str:
            cur.append(c)
            if c == "\\" and i + 1 < len(text):
                cur.append(text[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            cur.append(c)
        elif text.startswith("#\\", i):
            cur.append(text[i:i + 3])
            i += 2
        elif c in "([":
            depth += 1
            cur.append(c)
        elif c in ")]":
            depth -= 1
            cur.append(c)
        elif c == "," and depth <= 0 and not (cur and cur[-1] == "@") \
                and not (i > 0 and text[i - 1] in "`,"):
            vals.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    last = "".join(cur).strip()
    if last or vals:
        vals.append(last)
    return vals


def strip_trailing_comment(s):
    """Cut a ';comment' that follows whitespace outside any string."""
    in_str = False
    i = 0
    while i < len(s):
        c = s[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif s.startswith("#\\", i):
            i += 2
        elif c == ";" and i > 0 and s[i - 1].isspace():
            return s[:i]
        i += 1
    return s


def parse_expectation(text):
    """text (with italic markers) -> dict(values, italics, no_values)."""
    text = strip_trailing_comment(text).strip()
    plain = clean(text)
    if NO_VALUES_RE.match(plain.replace("&lt;", "<").replace("&gt;", ">")):
        return {"values": [], "italics": [], "no_values": True}
    vals = [v for v in split_values(text)]
    return {
        "values": [clean(v) for v in vals],
        "italics": [re.findall(IT0 + "(.*?)" + IT1, v, re.S) for v in vals],
        "no_values": False,
    }


STARTERS = "('`#;\"*+-0123456789<"


TRAIL_PROSE_RE = re.compile(r"^(.*?\))\s*(==.*|(?:is|has|should|are|will)\s[A-Za-z].*)$", re.S)
ERRORISH_RE = re.compile(r"\b(is an error|should signal an error|signals? an error|is erroneous)\b", re.I)


def is_prose(line):
    s = clean(line).strip()
    if s.startswith("==") or re.match(r"^\d+:\s", s):
        return True
    if re.match(r"^\(\s*-?\d", s):          # "(0 0)": printed data, not a form
        return True
    if not s or s[0] in STARTERS:
        return False
    return len(s.split()) > 1


class Step:
    def __init__(self, form, line):
        self.form = form          # accumulated form text (with markers)
        self.line = line
        self.exp = None           # first expectation dict
        self.exp_text = None      # text being accumulated for expectation
        self.alts = []            # OR alternatives (dicts)
        self.out = None           # list of output lines
        self.flags = []

    def form_open(self):
        d, s, _ = scan(self.form)
        return d > 0 or s

    def exp_open(self):
        if self.exp_text is None:
            return False
        d, s, _ = scan(self.exp_text, comments=False)
        # a trailing comma means more values follow on the next line
        return d > 0 or s or clean(self.exp_text).rstrip().endswith(",")

    def finish_exp(self):
        if self.exp_text is not None:
            parsed = parse_expectation(self.exp_text)
            if getattr(self, "_alt", False):
                self.alts.append(parsed)
            elif self.exp is None:
                self.exp = parsed
            else:
                self.alts.append(parsed)
            self.exp_text = None
            self._alt = False


def parse_block(text, base_line=0):
    """Parse one <pre> text into (steps, unparsed).

    steps: list of Step; unparsed: list of (line, text, reason)."""
    steps, unparsed = [], []
    cur = None

    def flush():
        nonlocal cur
        if cur is not None:
            cur.finish_exp()
            steps.append(cur)
            cur = None

    for k, raw in enumerate(text.split("\n")):
        lineno = base_line + k
        line = raw.rstrip()
        s = line.strip()
        plain = clean(s)
        if not s:
            if cur is not None and cur.exp_text is None and cur.form_open():
                cur.form += "\n"
                continue
            if cur is not None and cur.exp_open():
                cur.exp_text += "\n"
                continue
            continue          # blank line: keep cur, a result may follow
        # continuation of an unbalanced expected value
        if cur is not None and cur.exp_open():
            cur.exp_text += "\n" + s
            continue
        if plain.startswith(PRINT):
            if cur is None:
                unparsed.append((lineno, plain, "output line without a form"))
                continue
            cur.finish_exp()
            if cur.out is None:
                cur.out = []
            body = plain[1:]
            cur.out.append(body[1:] if body.startswith(" ") else body)
            continue
        m = re.match(r"^(OR\s*)?" + ARROW + r"\s*(.*)$", plain)
        if m:
            if cur is None:
                unparsed.append((lineno, plain, "result line without a form"))
                continue
            cur.finish_exp()
            # use the marker-bearing text
            body = s[s.index(ARROW) + 1:].strip()
            cur.exp_text = body
            cur._alt = bool(m.group(1)) or cur.exp is not None
            continue
        if cur is not None and cur.exp_text is None and cur.form_open():
            # continuation of a multi-line form
            _, _, arrow = scan(cur.form + "\n" + s)
            add_arrow_or_form(cur, s)
            continue
        # a new step starts here
        if s.startswith(";"):
            continue                  # comment-only line (cur kept pending)
        flush()
        pre_arrow = s.split(ARROW)[0]
        if is_prose(pre_arrow) and ARROW not in s:
            unparsed.append((lineno, plain, "prose"))
            continue
        cur = Step("", lineno)
        add_arrow_or_form(cur, s)
    flush()
    return steps, unparsed


def add_arrow_or_form(cur, s):
    """Append line s to cur's form, splitting at a top-level arrow."""
    sep = "\n" if cur.form else ""
    head, arr, tail = s.partition(ARROW)
    m = TRAIL_PROSE_RE.match(head)
    if m and scan(cur.form + sep + m.group(1))[0] == 0:
        cur.flags.append("trailing-prose")
        if ERRORISH_RE.search(clean(m.group(2))):
            cur.flags.append("expects-error")
        s = m.group(1) + (" " + arr + tail if arr else "")
    _, _, arrow = scan(cur.form + sep + s)
    if arrow is None:
        cur.form += sep + s
        return
    pos = arrow - len(cur.form + sep)
    cur.form += sep + s[:pos]
    cur.exp_text = s[pos + 1:].strip()
    cur._alt = False


def step_to_dict(st, entry, file, block):
    form = clean(st.form).strip()
    flags = list(st.flags)
    if IT0 in st.form:
        flags.append("italic-in-form")
    exp = st.exp
    d = {
        "secno": entry["secno"], "names": entry["names"], "kind": entry["kind"],
        "file": file, "block": block, "line": st.line,
        "form_text": form,
        "expected_values": exp["values"] if exp and not exp["no_values"] else None,
        "expected_italics": exp["italics"] if exp else None,
        "expected_output": st.out,
        "no_values": bool(exp and exp["no_values"]),
        "alternatives": [
            {"values": a["values"], "italics": a["italics"], "no_values": a["no_values"]}
            for a in st.alts],
        "flags": flags,
    }
    if exp is not None and not exp["no_values"] and not exp["values"]:
        d["expected_values"] = [""]
        d["flags"].append("empty-expectation")
    return d


def extract_entry(xml_bytes, file="<string>"):
    parser = etree.XMLParser(recover=True, resolve_entities=False, load_dtd=False)
    root = etree.fromstring(xml_bytes, parser)
    ns = {"x": "http://www.w3.org/1999/xhtml"}
    h3 = root.xpath("//x:h3[@class='entry']", namespaces=ns)
    if not h3:
        return None
    h3 = h3[0]
    def sp(c):
        r = h3.xpath("x:span[@class='%s']" % c, namespaces=ns)
        return "".join(r[0].itertext()).strip() if r else ""
    entry = {"secno": sp("secno"), "names": sp("names"), "kind": sp("kind"),
             "file": file, "steps": [], "unparsed": [], "blocks": 0}
    dts = root.xpath("//x:dt[normalize-space(string(.))='Examples:']", namespaces=ns)
    block = 0
    for dt in dts:
        dd = dt.getnext()
        if dd is None:
            continue
        for pre in dd.xpath(".//x:pre", namespaces=ns):
            block += 1
            sl = pre.sourceline or 0
            steps, unp = parse_block(pre_text(pre), sl)
            for st in steps:
                entry["steps"].append(step_to_dict(st, entry, file, block))
            for (ln, t, why) in unp:
                entry["unparsed"].append({"secno": entry["secno"], "names": entry["names"],
                                          "file": file, "block": block, "line": ln,
                                          "text": t, "reason": why})
    entry["blocks"] = block
    return entry if block else None


ELLIPSIS_RE = re.compile(r"(?<![\w.])\.\.\.(?![\w.])")


def finalize_unparsed(entry):
    """Steps whose form never closed cannot be evaluated: move to unparsed."""
    keep = []
    for st in entry["steps"]:
        d, s, _ = scan(st["form_text"])
        f = st["form_text"].strip()
        if f and not re.search(r"[(\s'`#\"]", f) and st["expected_values"] is None \
                and st["expected_output"] is None and not st["no_values"]:
            entry["unparsed"].append({**{k: st[k] for k in ("secno", "names", "file", "block", "line")},
                                      "text": f, "reason": "bare symbol without expectation"})
        elif not f:
            entry["unparsed"].append({**{k: st[k] for k in ("secno", "names", "file", "block", "line")},
                                      "text": "", "reason": "empty form"})
        elif d > 0 or s:
            entry["unparsed"].append({**{k: st[k] for k in ("secno", "names", "file", "block", "line")},
                                      "text": st["form_text"], "reason": "unbalanced form"})
        else:
            if ELLIPSIS_RE.search(re.sub(r'"(?:[^"\\]|\\.)*"', '""', f)):
                st["flags"].append("ellipsis-in-form")
            keep.append(st)
    entry["steps"] = keep
    return entry


def extract_all(text_dir):
    """Entries of every dictionary-entry file (found by markup, recursively), either layout."""
    entries = []
    for p in epub_entries.find_entry_files(text_dir):
        e = extract_entry(p.read_bytes(), epub_entries.rel_to_oebps(p, text_dir))
        if e:
            entries.append(finalize_unparsed(e))
    entries.sort(key=lambda e: [int(x) if x.isdigit() else x for x in re.split(r"[.]", e["secno"])])
    return entries


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--text-dir", default=str(Path(__file__).resolve().parent.parent / "src/OEBPS/text"))
    ap.add_argument("-o", "--out", help="write JSON here (default stdout)")
    a = ap.parse_args(argv)
    entries = extract_all(a.text_dir)
    js = json.dumps(entries, indent=1, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(js, encoding="utf-8")
    else:
        print(js)
    n = sum(len(e["steps"]) for e in entries)
    print(f"{len(entries)} entries, {n} steps, "
          f"{sum(len(e['unparsed']) for e in entries)} unparsed", file=sys.stderr)


if __name__ == "__main__":
    main()
