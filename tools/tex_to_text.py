#!/usr/bin/env python3
"""Approximate TeX -> plain-text normaliser for comparing dpANS3R entry text
with the EPUB.  It is deliberately lossy: the aim is that genuine wording
differences stand out from markup noise.  Unknown macros keep their argument
text (the braces are simply dropped) and are counted in ``stats``.

Sentence macros (\\Lazychecktype, \\Thefunction, ...) are expanded from
\\def definitions parsed out of the shared setup-*.tex files (``load_defs``).
"""
import re
import sys
from collections import Counter
from pathlib import Path

SECREF = "\u00a7"
LETTERS = re.compile(r"[A-Za-z]+")

# ---------------------------------------------------------------- \def parsing

def _balanced(s, i):
    """s[i] == '{'; return index just past the matching '}'."""
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return len(s)


DEF_RE = re.compile(r"\\def\s*\\([A-Za-z.]+)\s*((?:#\d\s*)*)\{")
LOCAL_DEF_RE = re.compile(r"\s*\\([A-Za-z.]+)\s*((?:#\d\s*)*)\{")


def parse_defs(text, only=None):
    """Return {name: (nargs, body)} for simple \\def\\name#1#2{body} lines."""
    text = "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("%"))
    defs = {}
    for m in DEF_RE.finditer(text):
        name = m.group(1)
        if only and not only(name):
            continue
        start = m.end() - 1
        end = _balanced(text, start)
        defs[name] = (len(re.findall(r"#\d", m.group(2))), text[start + 1:end - 1])
    return defs




def load_defs(root):
    root = Path(root)
    defs = {}
    for fname in ("setup-aux.tex", "setup-document.tex", "setup-terms.tex", "setup-sections.tex"):
        p = root / fname
        if p.exists():
            defs.update(parse_defs(p.read_text(encoding="latin-1")))
    return defs

# ------------------------------------------------------------------ primitives
# name -> (argspec, function)   argspec: number of args, or "w" for a
# word-delimited first argument followed by braced args e.g. "w{{".

def _id(a): return a
def _star(a): return a + "*"
def _plus(a): return a + "+"

SIMPLE_WRAP = """term param funref macref typeref varref specref declref conref f i b it bf tt rm
ff misc miscref loopref clref ttref arg word bit hbox mbox vbox vtop 
ang kwdref""".split()

CONST = {
    "nil": "nil", "t": "t", "empty": "()", "null": "null",
    "key": "&key", "opt": "&optional", "optional": "&optional", "rest": "&rest",
    "body": "&body", "whole": "&whole", "aux": "&aux", "environment": "&environment",
    "allowotherkeys": "&allow-other-keys",
    "EV": "\u2192", "OUT": "\u25b7", "EQ": "==", "OV": "OR\u2192", "NV": "NOT\u2192",
    "None": "None.", "clisp": "Common Lisp", "Lisp": "Lisp", "CLOS": "object system",
    "OS": "object system", "CLtL": "Common Lisp: The Language", "CLtLTwo": "Common Lisp: The Language, Second Edition",
    "eval": "evaluated", "noeval": "not evaluated", "evalspecial": "evaluated as described below",
    "etc": "etc.", "ie": "i.e.,", "eg": "e.g.,", "ldots": "...", "dots": "...",
    "noargs": "<no arguments>", "novalues": "<no values>",
    "bull": "\u2022", "cdot": "\u00b7", "pi": "pi", "le": "<=",
    "rightarrow": "\u2192", "downarrow": "\u2193", "Rightarrow": "\u21d2", "equiv": "\u2261",
    "ge": ">=", "ne": "/=", "times": "x", "vert": "|", "lparen": "(", "rparen": ")",
    "lbrack": "[", "rbrack": "]", "lbracket": "[", "rbracket": "]", "lbr": "[", "rbr": "]",
    "lcurly": "{", "rcurly": "}", "bq": "`", "alpha": "alpha", "epsilon": "epsilon",
    "schwa": "\u0259", "sqrt": "sqrt", "hat": "^",
    "Space": "Space", "SPACE": "SPACE", "Tab": "Tab", "Page": "Page", "Rubout": "Rubout",
    "Newline": "Newline", "Backspace": "Backspace", "Return": "Return", "Linefeed": "Linefeed",
    "Doublequote": '"', "TildeUnderscore": "~_", "Bell": "Bell", "Bigl": "", "Bigr": "", "bigl": "", "bigr": "", "left": "", "right": "",
    "par": "\n\n", "null": "", "TVar": "var", "GTVar": "var", "cr": "\n", "CR": "\n", "CRLF": "[Return]", "newline": "\n", "break": "\n",
    "quad": " ", "qquad": " ", "enspace": " ", "thinspace": " ", "space": " ", "sp": " ",
    "UniversalTime": "Universal Time", "Time": "Time",
    "thenextfigure": "the next figure", "Thenextfigure": "The next figure",
    "code": "\n", "endcode": "\n", "keyword": "", "log": "log", "plus": "+",
    "LeftParen": SECREF, "hfil": " ", "hfill": " ", "noindent": "", "indent": "",
    "medbreak": "\n", "smallbreak": "\n", "bigbreak": "\n", "eject": "", "relax": "",
    "dummy": "", "ignorespaces": "", "endgraf": "\n", "beginlist": "\n", "endlist": "\n",
    "begingroup": "", "endgroup": "", "bgroup": "", "egroup": "",
    "begininterleave": "[[", "endinterleave": "]]", "extrainterleave": "",
    "break": "\n",
}
# macros whose name is also a section-reference macro etc. are handled in render().

WRAP2 = {  # 2-arg macros: function of rendered args
    "newtermidx": lambda a, b: a,
    "auxbnf": lambda a, b: a + " ::= " + b,
}

ONE = {
    "kwd": lambda a: ":" + a,
    "keyref": lambda a: "&" + a,
    "packref": lambda a: a,
    "plus": lambda a: a + "+",
    "item": lambda a: "" if a.strip() == "\u2022" else a,
    "itemitem": lambda a: "" if a.strip() == "\u2022" else a,
    "itemitemitem": lambda a: "" if a.strip() == "\u2022" else a,
    "star": lambda a: a + "*",
    "starparam": lambda a: "{" + a + "}*",
    "plusparam": lambda a: "{" + a + "}+",
    "paren": lambda a: "(" + a + ")",
    "brac": lambda a: "[" + a + "]",
    "curly": lambda a: "{" + a + "}",
    "ttbrac": lambda a: "[" + a + "]",
    "down": lambda a: "\u2193" + a,
    "interleave": lambda a: "[[" + a + "]]",
    "IN": lambda a: a,
    "newterm": lambda a: a,
    "formatOp": lambda a: " ~" + a,
    "formatdirective": lambda a: "~" + a + " format directive",
    "metavar": lambda a: "<<" + a + ">>", "metaparam": lambda a: "<<" + a + ">>",
    "ang": lambda a: "<" + a + ">",
    "pronounced": lambda a: "[" + a + "]",
    "meaning": lambda a: a,
    "Stress": lambda a: a, "stress": lambda a: a,
    "editornote": lambda a: "", "reviewer": lambda a: "",  # setup-options.tex: \\editornotesfalse
    "issue": lambda a: "", "endissue": lambda a: "",
    "secref": lambda a: "Section " + SECREF,
    "chapref": lambda a: "Chapter " + SECREF,
    "figref": lambda a: "Figure " + SECREF,
    "idxref": lambda a: "",
    "idxterm": lambda a: "", "idxtext": lambda a: "", "idxcode": lambda a: "", "idxkwd": lambda a: "",
    "Figref": lambda a: "Figure " + SECREF,
    "sub": lambda a: a,
    "Seesection": lambda a: "See Section " + SECREF,
    "seesection": lambda a: "see Section " + SECREF,
    "Seechapter": lambda a: "See Chapter " + SECREF,
    "seechapter": lambda a: "see Chapter " + SECREF,
    "Seefigure": lambda a: "See Figure " + SECREF,
    "seefigure": lambda a: "see Figure " + SECREF,
    "uppercase": lambda a: a.upper(),
}

# Definition forms: first arg is a word, the rest braced.
def _def_sig(*parts):
    return " ".join(p for p in parts if p).strip()

DEFFORMS = {
    # name: (nargs, renderer(args))
    "Defun": (2, lambda a: _def_sig(a[0], a[1])),
    "DefunWithValues": (3, lambda a: _def_sig(a[0], a[1], "\u2192", a[2])),
    "DefunWithValuesNewline": (3, lambda a: _def_sig(a[0], a[1], "\u2192", a[2])),
    "DefunNoReturn": (2, lambda a: _def_sig(a[0], a[1], "\u2192|")),
    "Defmac": (2, lambda a: _def_sig(a[0], a[1])),
    "DefmacWithValues": (3, lambda a: _def_sig(a[0], a[1], "\u2192", a[2])),
    "DefmacWithValuesNewline": (3, lambda a: _def_sig(a[0], a[1], "\u2192", a[2])),
    "DefmacNoReturn": (2, lambda a: _def_sig(a[0], a[1], "\u2192|")),
    "Defspec": (2, lambda a: _def_sig(a[0], a[1])),
    "DefspecWithValues": (3, lambda a: _def_sig(a[0], a[1], "\u2192", a[2])),
    "DefspecWithValuesNewline": (3, lambda a: _def_sig(a[0], a[1], "\u2192", a[2])),
    "DefspecNoReturn": (2, lambda a: _def_sig(a[0], a[1], "\u2192|")),
    "Defgen": (2, lambda a: _def_sig(a[0], a[1])),
    "DefgenWithValues": (3, lambda a: _def_sig(a[0], a[1], "\u2192", a[2])),
    "DefgenWithValuesNewline": (3, lambda a: _def_sig(a[0], a[1], "\u2192", a[2])),
    "Defmeth": (2, lambda a: _def_sig(a[0], a[1])),
    "Defsetf": (3, lambda a: _def_sig("(setf (" + a[0], a[1] + ")", a[2] + ")")),
    "Deftype": (2, lambda a: "(" + a[0] + " " + a[1] + ")"),
    "Defvar": (1, lambda a: "*" + a[0] + "*"),
    "Defvarnoast": (1, lambda a: a[0]),
    "Defcon": (1, lambda a: a[0]),
}

TABLES = {"tablefigtwo": 4, "tablefigthree": 5, "tablefigfour": 6, "displaytwo": 2, "displaythree": 2,
          "displayfour": 2}
IGNORE_ARG1 = {"hskip", "vskip", "penalty", "kern", "setbox"}  # (not used; stats only)

SYMBOLS = {  # control symbols
    "\\": "\\", " ": " ", "\n": " ", "&": "&", "%": "%", "#": "#", "$": "$", "_": "_", "{": "{", "}": "}",
    ",": "", "/": "", "!": "", ";": "", ":": "", ">": "", "<": "", "-": "", "=": "", "+": "",
    "'": "", "`": "", "^": "", '"': "", "~": "~", "|": "|", ".": "", "*": "", "@": "",
}


class Renderer:
    def __init__(self, defs=None, stats=None):
        self.defs = defs or {}
        self.stats = stats if stats is not None else Counter()

    # -- argument reading ---------------------------------------------------
    def read_arg(self, s, i, word=False):
        n = len(s)
        while i < n and s[i] in " \t\n":
            i += 1
        if i >= n:
            return "", i
        if s[i] == "{":
            j = _balanced(s, i)
            return s[i + 1:j - 1], j
        if s[i] == "\\":
            m = LETTERS.match(s, i + 1)
            if m:
                return s[i:m.end()], m.end()
            return s[i:i + 2], i + 2
        if word:
            m = re.compile(r"[^\s{}\\]+").match(s, i)
            if m:
                return m.group(0), m.end()
        return s[i], i + 1

    # -- main ----------------------------------------------------------------
    def render(self, s, depth=0, lit=False):
        """Render TeX source.  \\code...\\endcode spans are rendered literally
        (no ligatures, $ and ~ are ordinary characters)."""
        if lit:
            return self._render(s, depth, True)
        if "\\code" in s:
            parts = []
            pos = 0
            for m in re.finditer(r"\\code\b(.*?)\\endcode\b", s, re.S):
                parts.append(self._render(s[pos:m.start()], depth, False))
                parts.append("\n" + self._render(m.group(1), depth, True) + "\n")
                pos = m.end()
            parts.append(self._render(s[pos:], depth, False))
            return "".join(parts)
        return self._render(s, depth, False)

    def _render(self, s, depth, lit):
        if depth > 12:
            return s
        out = []
        i, n = 0, len(s)
        while i < n:
            c = s[i]
            if c == "\\":
                if i + 1 >= n:
                    break
                d = s[i + 1]
                m = LETTERS.match(s, i + 1)
                if not m:
                    out.append(SYMBOLS.get(d, ""))
                    if d not in SYMBOLS:
                        self.stats["\\" + d] += 1
                    i += 2
                    continue
                name = m.group(0)
                i = m.end()
                if name == "etc" and s[i:i + 1] == ".":
                    i += 1
                text, i = self.macro(name, s, i, depth)
                out.append(text)
            elif c in "{}":
                i += 1
            elif lit and c in "$~":
                out.append(c); i += 1
            elif c == "$" or (c in "^_" and not lit):
                i += 1  # math shifts, super/subscripts
            elif c == "&" and not lit:
                out.append(" "); i += 1  # column separator (a literal & is written \\&)
            elif c == "~":
                out.append(" ")
                i += 1
            elif lit and c in "-`'":
                out.append(c); i += 1
            elif c == "`" and s[i:i + 2] == "``":
                out.append('"'); i += 2
            elif c == "'" and s[i:i + 2] == "''":
                out.append('"'); i += 2
            elif c == "-" and s[i:i + 3] == "---":
                out.append("\u2014"); i += 3
            elif c == "-" and s[i:i + 2] == "--":
                out.append("\u2013"); i += 2
            else:
                out.append(c)
                i += 1
        return "".join(out)

    def macro(self, name, s, i, depth):
        """Render macro `name` whose arguments start at s[i]; return (text, next index)."""
        if name == "def":
            m = LOCAL_DEF_RE.match(s, i)
            if m:
                end = _balanced(s, m.end() - 1)
                self.defs[m.group(1)] = (len(re.findall(r"#\d", m.group(2))), s[m.end():end - 1])
                return "", end
        if name in ("DefunMultiWithValues", "DefunMultiAccessorWithValues", "DefsetfMulti"):
            nargs = 3 if name in ("DefunMultiWithValues", "DefsetfMulti") else 4
            args = []
            j = i
            for _ in range(nargs):
                a, j = self.read_arg(s, j)
                args.append(a)
            ents = []
            body = args[-1]
            for m in re.finditer(r"\\entry", body):
                e, _ = self.read_arg(body, m.end())
                ents.append(self.render(e, depth + 1).strip())
            r = [self.render(a, depth + 1).strip() for a in args[:-1]]
            lines = []
            for e in ents:
                if name == "DefsetfMulti":
                    lines.append("(setf (" + e + " " + r[0] + ") " + r[1] + ")")
                elif name == "DefunMultiWithValues":
                    lines.append(" ".join([e, r[0], "\u2192", r[1]]))
                else:
                    lines.append(" ".join([e, r[0], "\u2192", r[1]]) + " | (setf (" + e + " " + r[0] + ") " + r[2] + ")")
            return "\n".join(lines) + "\n", j
        if name == "DocMethods":  # used once (documentation); its body defines \\Meth twice
            title, j = self.read_arg(s, i)
            body, j = self.read_arg(s, j)
            meths = []
            for m in re.finditer(r"\\Meth", body):
                a, k = self.read_arg(body, m.end())
                b, _ = self.read_arg(body, k)
                meths.append((a.strip(), b.strip()))
            lines = [self.render(title, depth + 1).strip() + ":"]
            for head in ("documentation", "(setf documentation) new-value"):
                for a, b in meths:
                    lines.append(f"{head} (x {a}) (doc-type (eql '{b}))")
            return "\n".join(lines) + "\n", j
        if name == "Vskip":
            m = re.compile(r"[^!]*!").match(s, i)
            return "", (m.end() if m else i)
        if name in DEFFORMS:
            nargs, fn = DEFFORMS[name]
            args = []
            j = i
            for k in range(nargs):
                a, j = self.read_arg(s, j, word=(k == 0))
                args.append(self.render(a, depth + 1).strip())
            return " " + fn(args) + " ", j
        if name in ONE:
            a, j = self.read_arg(s, i)
            if name in ("secref", "chapref", "figref", "Seesection", "seesection", "Seechapter",
                        "seechapter", "Seefigure", "seefigure"):
                ref = a.strip().lstrip("\\")
                kind = None
                if ref in self.defs:  # the section macro's own text says Section or Chapter
                    first = self.defs[ref][1].lstrip().split(" ", 1)[0]
                    kind = first if first in ("Section", "Chapter") else None
                if kind and name in ("secref", "chapref", "Seesection", "seesection", "Seechapter", "seechapter"):
                    pre = {"Seesection": "See ", "seesection": "see ", "Seechapter": "See ", "seechapter": "see "}.get(name, "")
                    return pre + kind + " " + SECREF, j
                return ONE[name](a), j
            return ONE[name](self.render(a, depth + 1)), j
        if name in WRAP2:
            a, j = self.read_arg(s, i)
            b, j = self.read_arg(s, j)
            return WRAP2[name](self.render(a, depth + 1), self.render(b, depth + 1)), j
        if name in TABLES:
            args = []
            j = i
            for _ in range(TABLES[name]):
                a, j = self.read_arg(s, j)
                args.append(self.render(a, depth + 1))
            return "Figure " + SECREF + " " + " ".join(args) + " ", j
        if name in SIMPLE_WRAP:
            a, j = self.read_arg(s, i)
            return self.render(a, depth + 1, lit=(name in ("f", "tt"))), j
        if name in CONST:
            t = CONST[name]
            return (" " + t + " " if name in ("EV", "OUT", "EQ", "OV", "NV") else t), i
        if name in self.defs:
            nargs, body = self.defs[name]
            args = []
            j = i
            for _ in range(nargs):
                a, j = self.read_arg(s, j)
                args.append(a)
            body = body.replace("##", "\x00")
            for k in range(nargs, 0, -1):
                body = body.replace("#%d" % k, args[k - 1])
            body = body.replace("\x00", "#")
            body = re.sub(r"Section\s+\d[\d.]*\s*\([^)]*\)", "Section " + SECREF, body)
            return self.render(body, depth + 1), j
        if name in ("begin", "end"):
            return "", i
        self.stats["\\" + name] += 1
        return "", i


_FOLD = {
    "\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'", "\u00a0": " ",
    "\u2212": "-", "\u2010": "-", "\u2011": "-",
}


def normalize_text(s):
    """Whitespace/quote normalisation applied to BOTH sides before comparing."""
    for k, v in _FOLD.items():
        s = s.replace(k, v)
    s = s.replace("\u2013", "--")
    s = re.sub(r"\s*(\u2014|--)\s*", r"\1", s)
    return " ".join(s.split())


def tex_to_text(tex, defs=None, stats=None):
    r = Renderer(defs, stats)
    return normalize_text(r.render(tex))


def main():
    root = sys.argv[1]
    defs = load_defs(root)
    print(len(defs), "defs loaded")


if __name__ == "__main__":
    main()
