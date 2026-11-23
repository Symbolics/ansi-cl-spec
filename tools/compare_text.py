#!/usr/bin/env python3
"""Compare the EPUB dictionary entries with the dpANS3R TeX sources.

    python3 tools/compare_text.py [--epub src/OEBPS/text] [--tex DIR] [--out audit/text]

Writes <out>/findings.json (every entry) and <out>/summary.md.  If --tex is not
given the sources are fetched (checksum-verified) into vendor/dpans/merged.
"""
import argparse
import difflib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import epub_entries  # noqa: E402
import tex_entries  # noqa: E402
import tex_to_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
_PUNCT = r",.;!?()\[\]{}<>|\"\u2192\u25b7\u2261"
TOKEN_RE = re.compile(r"::=|==|(?:(?!::=|==)[^\s" + _PUNCT + r"])+|[" + _PUNCT + r"]")


def tokens(s):
    return TOKEN_RE.findall(s)


def diff_ops(a, b, cap=40):
    """Word-level diff of token lists a (TeX) and b (EPUB): (ratio, ops)."""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ops = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        ops.append({
            "op": tag,
            "tex": " ".join(a[i1:i2]),
            "epub": " ".join(b[j1:j2]),
            "ctx": " ".join(a[max(0, i1 - 4):i1]),
        })
    return sm.ratio(), ops[:cap], len(ops)


def norm_name(n, defs, stats):
    return tex_to_text.normalize_text(tex_to_text.tex_to_text(n, defs, stats))


def prep_tex(entries, defs, stats, tex_dir=None):
    file_defs = {}
    for e in entries:
        if tex_dir and e["source"] not in file_defs:
            txt = (Path(tex_dir) / e["source"]).read_text(encoding="latin-1")
            file_defs[e["source"]] = {**defs, **tex_to_text.parse_defs(tex_entries.strip_comments(txt))}
        defs_e = file_defs.get(e["source"], defs)
        e["names"] = [norm_name(n, defs_e, stats) for n in e["names"]]
        e["sections"] = [dict(s, text=tex_to_text.tex_to_text(s["raw"], defs_e, stats) if not s["empty"] else "")
                         for s in e["sections"]]
    return entries


def epub_norm(entries):
    for e in entries:
        for s in e["sections"]:
            # figure numbers: the EPUB writes "Figure 2-9" where the TeX has a \\figref
            s["text"] = re.sub(r"Figure\s+\d+-\d+\.?", "Figure " + tex_to_text.SECREF, s["text"])
        e["names"] = [tex_to_text.normalize_text(n) for n in e["names"]]
        for s in e["sections"]:
            s["text"] = tex_to_text.normalize_text(s["text"])
    return entries


def match(tex, epub):
    """Return (pairs, tex_only, epub_only, how) where how[idx] is the pass used."""
    pairs, how = [], {}
    unt = list(range(len(tex)))
    une = list(range(len(epub)))
    passes = [
        ("exact", lambda e: (e["chapter"], tuple(e["names"]), e["kind"])),
        ("same-name-set", lambda e: (e["chapter"], frozenset(e["names"]), e["kind"])),
        ("first-name", lambda e: (e["chapter"], e["names"][0], e["kind"])),
    ]
    for pname, kf in passes:
        buckets = defaultdict(list)
        for j in une:
            buckets[kf(epub[j])].append(j)
        nt, used = [], set()
        for i in unt:
            b = buckets.get(kf(tex[i]))
            if b:
                j = b.pop(0)
                pairs.append((i, j))
                how[(i, j)] = pname
                used.add(j)
            else:
                nt.append(i)
        unt = nt
        une = [j for j in une if j not in used]
    return pairs, unt, une, how


def align_sections(ts, es):
    """Pair sections by (label, occurrence).  Returns list of (label, tex|None, epub|None)."""
    def keyed(secs):
        seen = Counter()
        d = {}
        for s in secs:
            k = (s["label"], seen[s["label"]])
            seen[s["label"]] += 1
            d[k] = s
        return d
    kt, ke = keyed(ts), keyed(es)
    out = []
    for k in kt:
        out.append((k[0], kt[k], ke.get(k)))
    for k in ke:
        if k not in kt:
            out.append((k[0], None, ke[k]))
    return out


def compare(tex, epub, how_pairs):
    pairs, tex_only, epub_only, how = how_pairs
    findings = []
    for i, j in sorted(pairs, key=lambda p: (epub[p[1]]["secno"] and [int(x) for x in epub[p[1]]["secno"].split(".")])):
        t, e = tex[i], epub[j]
        tsecs = [s for s in t["sections"] if not s["empty"]]
        tsecs_all = [s["label"] for s in t["sections"]]
        tl = [s["label"] for s in tsecs]
        el = [s["label"] for s in e["sections"]]
        # Does the EPUB include empty \None sections?
        empty_in_epub = [s["label"] for s in t["sections"]
                         if s["empty"] and s["label"] in el and s["label"] not in tl]
        f = {
            "secno": e["secno"],
            "names": e["names"],
            "kind": e["kind"],
            "epub_file": e["file"],
            "tex_file": t["source"],
            "match": how[(i, j)],
            "names_equal": t["names"] == e["names"],
            "kind_equal": t["kind"] == e["kind"],
            "tex_names": t["names"],
            "tex_kind": t["kind"],
            "labels_equal": tl == el,
            "label_diff": None if tl == el else {"tex": tl, "epub": el},
            "empty_sections_in_tex": [s["label"] for s in t["sections"] if s["empty"]],
            "empty_sections_present_in_epub": empty_in_epub,
            "sections": [],
        }
        for label, ts, es in align_sections(tsecs, e["sections"]):
            if ts is None or es is None:
                f["sections"].append({"label": label, "only_in": "epub" if ts is None else "tex",
                                      "ratio": 0.0, "diffs": []})
                continue
            ratio, ops, nops = diff_ops(tokens(ts["text"]), tokens(es["text"]))
            f["sections"].append({"label": label, "ratio": round(ratio, 4),
                                  "tex_words": len(tokens(ts["text"])), "epub_words": len(tokens(es["text"])),
                                  "n_diffs": nops, "diffs": ops if ratio < 1.0 else []})
        f["min_ratio"] = min([s["ratio"] for s in f["sections"]] or [1.0])
        findings.append(f)
    return findings


def build_summary(findings, tex_only, epub_only, stats, n_tex, n_epub, notes):
    L = []
    w = L.append
    only = [(f, s) for f in findings for s in f["sections"] if "only_in" in s]
    pron = [(f, s) for f in findings for s in f["sections"] if s["label"] == "Pronunciation" and "only_in" not in s]
    secs = [(f, s) for f in findings for s in f["sections"] if "only_in" not in s]
    ratios = [s["ratio"] for _, s in secs]
    w("# Text fidelity: EPUB vs dpANS3R\n")
    w("Generated by `tools/compare_text.py` (TeX normaliser: `tools/tex_to_text.py`). Keys are section number + names.\n")
    w("## Counts\n")
    w(f"- TeX entries: {n_tex}; EPUB entries: {n_epub}; matched: {len(findings)}; "
      f"TeX-only: {len(tex_only)}; EPUB-only: {len(epub_only)}")
    how = Counter(f["match"] for f in findings)
    w(f"- match passes: {dict(how)}")
    w(f"- names differ: {sum(not f['names_equal'] for f in findings)}; "
      f"kind differs: {sum(not f['kind_equal'] for f in findings)}; "
      f"label sequence differs: {sum(not f['labels_equal'] for f in findings)}")
    w(f"- sections present on one side only: {len(only)}")
    emp = sum(len(f["empty_sections_in_tex"]) for f in findings)
    emp_in = sum(len(f["empty_sections_present_in_epub"]) for f in findings)
    w(f"- empty (`\\None`) sections in TeX: {emp}; of those present in the EPUB: {emp_in}. "
      f"**Convention: the EPUB omits empty sections** ({emp_in} exception(s)); this matches the dpANS build option "
      f"`\\nullabelfalse` in setup-options.tex, which also omits them from the printed standard.")
    w(f"- sections compared: {len(secs)}; exact (ratio 1.0): {sum(r == 1.0 for r in ratios)}; "
      f"below 0.99: {sum(r < 0.99 for r in ratios)}; below 0.95: {sum(r < 0.95 for r in ratios)}; "
      f"below 0.80: {sum(r < 0.80 for r in ratios)}")
    w(f"- entries with every section exact and labels equal: "
      f"{sum(f['min_ratio'] == 1.0 and f['labels_equal'] for f in findings)}\n")
    w("## Distribution of section ratios\n")
    w("| ratio | sections |\n|---|---|")
    edges = [(1.0, 1.0001, "= 1.0"), (0.99, 1.0, "0.99 - <1.0"), (0.98, 0.99, "0.98 - 0.99"),
             (0.95, 0.98, "0.95 - 0.98"), (0.90, 0.95, "0.90 - 0.95"), (0.80, 0.90, "0.80 - 0.90"),
             (0.50, 0.80, "0.50 - 0.80"), (-1, 0.50, "< 0.50")]
    for lo, hi, name in edges:
        w(f"| {name} | {sum(lo <= r < hi for r in ratios)} |")
    w("")
    if notes:
        w("## Normaliser iterations and equivalences\n")
        for n in notes:
            w(n)
        w("")
    w("## Unmatched entries\n")
    w("TeX-only: " + (", ".join(f"{e['chapter']}: {', '.join(e['names'])} ({e['kind']})" for e in tex_only) or "none"))
    w("\nEPUB-only: " + (", ".join(f"{e['secno']} {', '.join(e['names'])} ({e['kind']})" for e in epub_only) or "none") + "\n")
    w("## Name / kind / label mismatches\n")
    any_ = False
    for f in findings:
        bits = []
        if not f["names_equal"]:
            bits.append(f"names: tex `{', '.join(f['tex_names'])}` vs epub `{', '.join(f['names'])}`")
        if not f["kind_equal"]:
            bits.append(f"kind: tex `{f['tex_kind']}` vs epub `{f['kind']}`")
        if not f["labels_equal"]:
            d = f["label_diff"]
            tl, el = d["tex"], d["epub"]
            bits.append("labels: tex-only " + str([x for x in tl if x not in el]) + ", epub-only " + str([x for x in el if x not in tl])
                        + ("" if set(tl) != set(el) else f" (order: tex {tl} vs epub {el})"))
        if bits:
            any_ = True
            w(f"- {f['secno']} {', '.join(f['names'])} ({f['kind']}): " + "; ".join(bits))
    if not any_:
        w("none")
    w("")
    w("## Lowest-ratio sections (top 60)\n")
    w(f"(Pronunciation sections are excluded here: {len(pron)} sections, mean ratio "
      f"{sum(s['ratio'] for _, s in pron) / max(1, len(pron)):.2f}; the TeX uses Webster-style accent macros that the "
      f"normaliser cannot render, so they are a notation difference, not a wording one.)\n")
    worst = sorted([x for x in secs if x[1]["label"] != "Pronunciation"], key=lambda fs: (fs[1]["ratio"], fs[0]["secno"]))[:60]
    for f, s in worst:
        w(f"### {f['secno']} {', '.join(f['names'])} -- {s['label']}  (ratio {s['ratio']}, {s.get('n_diffs', 0)} diffs)\n")
        if "only_in" in s:
            w(f"- section only in {s['only_in']}\n")
            continue
        for d in s["diffs"][:4]:
            w(f"- {d['op']}: `...{d['ctx']}` tex: `{clip(d['tex'])}` | epub: `{clip(d['epub'])}`")
        w("")
    w("## Unknown TeX macros left (top 40; argument text kept)\n")
    w(", ".join(f"`{k}`:{v}" for k, v in stats.most_common(40)) or "none")
    w("")
    return "\n".join(L)


def clip(s, n=90):
    s = s.replace("`", "'")
    return s if len(s) <= n else s[: n - 3] + "..."


def run(epub_dir, tex_dir, out_dir, notes=()):
    defs = tex_to_text.load_defs(tex_dir)
    stats = Counter()
    tex = prep_tex(tex_entries.parse_tree(tex_dir), defs, stats, tex_dir)
    epub = epub_norm(epub_entries.parse_tree(epub_dir))
    m = match(tex, epub)
    findings = compare(tex, epub, m)
    pairs, tex_only, epub_only, how = m
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = {
        "tex_entries": len(tex), "epub_entries": len(epub),
        "tex_only": [{"chapter": tex[i]["chapter"], "names": tex[i]["names"], "kind": tex[i]["kind"]} for i in tex_only],
        "epub_only": [{"secno": epub[j]["secno"], "names": epub[j]["names"], "kind": epub[j]["kind"]} for j in epub_only],
        "unknown_macros": dict(stats.most_common()),
        "entries": findings,
    }
    (out / "findings.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "summary.md").write_text(
        build_summary(findings, [tex[i] for i in tex_only], [epub[j] for j in epub_only], stats,
                      len(tex), len(epub), list(notes)), encoding="utf-8")
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epub", default=str(ROOT / "src/OEBPS/text"))
    ap.add_argument("--tex")
    ap.add_argument("--out", default=str(ROOT / "audit/text"))
    ap.add_argument("--notes-file", default=str(ROOT / "audit/text/normaliser-notes.md"),
                    help="markdown inserted verbatim into the summary (normaliser iteration notes)")
    a = ap.parse_args()
    tex_dir = a.tex
    if not tex_dir:
        import fetch_dpans
        tex_dir = str(fetch_dpans.fetch())
    notes = Path(a.notes_file).read_text().splitlines() if a.notes_file and Path(a.notes_file).exists() else []
    f = run(a.epub, tex_dir, a.out, notes)
    print(f"{len(f)} entries compared; see {a.out}/summary.md")


if __name__ == "__main__":
    main()
