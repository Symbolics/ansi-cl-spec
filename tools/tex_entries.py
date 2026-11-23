#!/usr/bin/env python3
"""Parse dpANS3(R) dictionary TeX files (dict-*.tex) into entries.

An entry is \\begincom{names}\\ftype{Kind} ... \\endcom.  Sections are introduced
by "\\label Name::" (or "\\label Name:\\None." for an empty section).
"""
import re
import sys
from pathlib import Path

LABEL_RE = re.compile(r"\\label\s+([^:\n]+?)\s*:(:|\\None[.!]?)")
BEGINCOM_RE = re.compile(r"\\begincom\{(.*?)\}\s*\\ftype\{(.*?)\}", re.S)
CODE_RE = re.compile(r"\\code\b.*?\\endcode\b", re.S)
INCLUDE_RE = re.compile(r"\\includeDictionary\{([^}]+)\}")


_COMMENT_TAIL = re.compile(r"((?:[^\\%]|\\.)*)%.*")


def strip_comments(text):
    """Remove TeX comments.  Outside \\code blocks a comment runs from an
    unescaped % to the end of the line.  Inside \\code...\\endcode a % is an
    ordinary character (format directives such as ~% appear there) except at the
    start of a line, where it still introduces a comment line."""
    lines = []
    in_code = False
    for line in text.split("\n"):
        if line.lstrip().startswith("%"):
            continue  # whole-line comment (the newline goes with it)
        if not in_code:
            m = _COMMENT_TAIL.fullmatch(line)
            code_part = m.group(1) if m else line
            if m:
                line = m.group(1)
            if re.search(r"\\code\b", code_part) and not re.search(r"\\endcode\b", code_part.split("\\code", 1)[1]):
                in_code = True
        elif re.search(r"\\endcode\b", line):
            in_code = False
        lines.append(line)
    return "\n".join(lines)


def norm_kind(kind):
    kind = " ".join(kind.split())
    return " ".join(w[:1].upper() + w[1:] if w.islower() else w for w in kind.split(" "))


def split_names(raw):
    return [" ".join(n.split()) for n in raw.split(",") if n.strip()]


def expand_label_macros(text):
    """Some dictionary files define one-argument macros whose body contains
    \\label lines (e.g. \\realtypespec in dict-numbers.tex); expand their
    invocations textually so the generated sections are seen."""
    for m in re.finditer(r"\\def\s*\\([A-Za-z]+)\s*#1\s*\{", text):
        start = m.end() - 1
        depth, j = 0, start
        while j < len(text):
            if text[j] == "\\":
                j += 2
                continue
            depth += 1 if text[j] == "{" else -1 if text[j] == "}" else 0
            j += 1
            if depth == 0:
                break
        body = text[start + 1:j - 1]
        if "\\label" not in body:
            continue
        name = m.group(1)
        head, tail = text[:start], text[j:]
        tail = re.sub(r"\\" + name + r"\{([^}]*)\}", lambda mm: body.replace("#1", mm.group(1)), tail)
        text = head + "{" + body + "}" + tail
        break  # one such macro per file is all that exists; keep it simple
    return text


def parse_dict_text(text, source="", chapter=None):
    """Parse the text of one dict file; return a list of entry dicts."""
    text = strip_comments(text)
    text = expand_label_macros(text)
    entries = []
    matches = list(BEGINCOM_RE.finditer(text))
    for m in matches:
        end = text.find("\\endcom", m.end())
        body = text[m.end(): end if end >= 0 else len(text)]
        sections = []
        labels = list(LABEL_RE.finditer(body))
        for i, lm in enumerate(labels):
            stop = labels[i + 1].start() if i + 1 < len(labels) else len(body)
            empty = lm.group(2) != ":"
            chunk = body[lm.end():stop].strip()
            if empty:
                # An empty label prints nothing, so any text that follows it
                # continues the previous section (as TeX would typeset it).
                sections.append({"label": " ".join(lm.group(1).split()), "empty": True, "raw": ""})
                if chunk:
                    prev = [x for x in sections if not x["empty"]]
                    if prev:
                        prev[-1]["raw"] = (prev[-1]["raw"] + "\n\n" + chunk).strip()
                        prev[-1]["absorbed"] = prev[-1].get("absorbed", []) + [sections[-1]["label"]]
                continue
            sections.append({"label": " ".join(lm.group(1).split()), "empty": False, "raw": chunk})
        entries.append({
            "chapter": chapter,
            "source": source,
            "names": split_names(m.group(1)),
            "kind": norm_kind(m.group(2)),
            "sections": sections,
            "preamble": body[: labels[0].start()].strip() if labels else body.strip(),
        })
    return entries


def chapter_map(root):
    """dict file stem -> chapter number, from \\includeDictionary in chap-N.tex."""
    cmap = {}
    for p in Path(root).glob("chap-*.tex"):
        m = re.fullmatch(r"chap-(\d+)\.tex", p.name)
        if not m:
            continue
        for inc in INCLUDE_RE.findall(p.read_text(encoding="latin-1")):
            cmap[inc] = int(m.group(1))
    return cmap


def parse_tree(root):
    root = Path(root)
    cmap = chapter_map(root)
    entries = []
    for p in sorted(root.glob("dict-*.tex"), key=lambda p: (cmap.get(p.stem, 99), p.name)):
        entries += parse_dict_text(p.read_text(encoding="latin-1"), p.name, cmap.get(p.stem))
    return entries


if __name__ == "__main__":
    es = parse_tree(sys.argv[1])
    print(len(es), "entries")
