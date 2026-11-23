#!/usr/bin/env python3
"""Step 5: repoint index links from legacy DictEntry_ fragments to per-symbol anchors.

For each index entry <b>NAME</b> and each of its links whose fragment is a DictEntry_ heading id
whose names include NAME, the fragment becomes NAME's per-symbol anchor (URL-safe). The symbols that
step 4 anchored outside entry headings are repointed through the explicit table STEP4 (same file,
old fragment -> new anchor). Everything else is left alone. Idempotent; --check writes nothing.
"""
import argparse
import posixpath
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anchors import name_to_fragment, xml_unescape  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / "src" / "OEBPS" / "text"

LL = "3-evaluation-and-compilation/3.4-lambda-lists.xhtml"
OPT = "3-evaluation-and-compilation/3.8.25-optimize.xhtml"
# symbol -> (file, old fragment) of the single link to repoint (anchors added in step 4).
# `structure` is deliberately absent: its Sharpsign S link keeps the section anchor (step 4 adds its
# documentation link, which is already per-symbol).
STEP4 = {
    "&allow-other-keys": (LL, "SubSubSubSec_Suppressing__248"),
    "&aux": (LL, "SubSubSectio_Specifiers_f_250"),
    "&body": (LL, "SubSection_Macro_Lambda_254"),
    "&environment": (LL, "SubSection_Macro_Lambda_254"),
    "&whole": (LL, "SubSection_Macro_Lambda_254"),
    "&key": (LL, "SubSubSectio_Specifiers_f_247"),
    "&optional": (LL, "SubSubSectio_Specifiers_f_245"),
    "&rest": (LL, "SubSubSectio_A_specifier__246"),
    "compilation-speed": (OPT, "DictEntry_optimize_307"),
    "debug": (OPT, "DictEntry_optimize_307"),
    "safety": (OPT, "DictEntry_optimize_307"),
    "space": (OPT, "DictEntry_optimize_307"),
    "speed": (OPT, "DictEntry_optimize_307"),
    "otherwise": ("5-data-and-control-flow/5.3.46-case.xhtml", "DictEntry_case_ccase_432"),
    "standard": ("7-objects/7.6-generic-functions-and-methods.xhtml", "SubSubSectio_Standard_Met_552"),
}

HEADING_RE = re.compile(r'<h3 id="(DictEntry_[^"]*)" class="entry">(.*?)</h3>', re.S)
SYMBOL_RE = re.compile(r'data-symbol="([^"]*)"')
TOKEN_RE = re.compile(r'<b>(.*?)</b>|<a href="([^"]*)"', re.S)


def entry_names(text_dir):
    """{(relpath, DictEntry id): set of lowercase unescaped names}"""
    out = {}
    for p in sorted(Path(text_dir).rglob("*.xhtml")):
        rel = p.relative_to(text_dir).as_posix()
        if rel.startswith("index/"):
            continue
        t = p.read_bytes().decode("utf-8")
        for m in HEADING_RE.finditer(t):
            out[(rel, m.group(1))] = {xml_unescape(s).lower() for s in SYMBOL_RE.findall(m.group(2))}
    return out


def repoint(text, rel, entries, stats):
    """Return text with links repointed; updates STATS (dict of counters/lists)."""
    out, pos, name = [], 0, None
    for m in TOKEN_RE.finditer(text):
        if m.group(1) is not None:
            name = " ".join(xml_unescape(re.sub(r"<[^>]+>", "", m.group(1))).split()).lower()
            continue
        href = m.group(2)
        path, _, frag = href.partition("#")
        if not frag or name is None:
            continue
        target = posixpath.normpath(posixpath.join(posixpath.dirname(rel), path))
        new = None
        if name in STEP4 and STEP4[name] == (target, frag):
            new = name_to_fragment(name)
            stats["step4"] += 1
        elif frag.startswith("DictEntry_"):
            names = entries.get((target, frag))
            if names is not None and name in names:
                new = name_to_fragment(name)
                stats["entry"] += 1
            else:
                stats["unmatched"].append((rel, name, href))
                continue
        else:
            stats["other"] += 1
            continue
        start = m.start(2) + len(path) + 1
        out.append(text[pos:start])
        out.append(new)
        pos = m.end(2)
    out.append(text[pos:])
    return "".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="dry run")
    ap.add_argument("--text-dir", default=str(TEXT))
    a = ap.parse_args(argv)
    base = Path(a.text_dir)
    entries = entry_names(base)
    stats = {"entry": 0, "step4": 0, "other": 0, "unmatched": []}
    for p in sorted((base / "index").glob("*.xhtml")):
        old = p.read_bytes().decode("utf-8")
        new = repoint(old, p.relative_to(base).as_posix(), entries, stats)
        if new != old and not a.check:
            p.write_bytes(new.encode("utf-8"))
    # on a re-run, already repointed links are counted as "other"; the first run's numbers are the report
    print(f"05_index_repoint: {'would repoint' if a.check else 'repointed'} {stats['entry']} entry links "
          f"+ {stats['step4']} step-4 links; left (non-DictEntry fragments or already done): {stats['other']}; "
          f"DictEntry links whose name is not in the target entry: {len(stats['unmatched'])}")
    for rel, name, href in stats["unmatched"]:
        print(f"  unmatched: {rel}: {name!r} -> {href}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
