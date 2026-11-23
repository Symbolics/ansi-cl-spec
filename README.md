# ansi-cl-spec

An EPUB 3 edition of the draft ANSI Common Lisp standard. **The edition is the source of
truth**: `src/` is the unpacked EPUB and is edited directly; the `.epub` is built from it.

## Layout

- `original/` the untouched input EPUB (provenance); git tag `v0-original` is the first import.
- `src/` unpacked EPUB tree (`mimetype`, `META-INF/`, `OEBPS/`).
- `tools/` Python tooling (`build.py`, `audit.py`, `roundtrip.py`); `tools/lisp/` SBCL scripts;
  `tools/data/cl-symbols.txt` the 978 external `COMMON-LISP` symbols.
- Content layout (`src/OEBPS/text/`): `cover.xhtml`, `<n>-<title-slug>/` per chapter (`14-conses/`,
  `A-appendix/`, `26-glossary/`) holding `index.xhtml` (chapter), `<secno>-<slug>.xhtml` (sections,
  e.g. `14.1-cons-concepts`) and dictionary entries (`14.2.9-car.xhtml`), plus `index/<letter>.xhtml`.
  Glossary letters are `26-glossary/<letter>.xhtml`. The section number makes every name unique;
  the slug is only for readability. `tools/data/path-map.json` maps the original flat names
  (`c14`, `s14-1`, `e14-2-9`, `g-a`, `i-a`) to these paths; `tools/rename_map.py`,
  `rename_apply.py` and `verify_rename.py` produced and checked that one-time rename.
- `tests/` pytest suite for the tools (small fixture trees, not the real book).
- `dist/` build output (git-ignored): `ANSI-Common-Lisp.epub`, `epubcheck.txt`, `audit.json`.

## Use

- `./build.sh [--src DIR] [--out FILE]` builds a deterministic EPUB (`dist/ANSI-Common-Lisp.epub`).
  `SOURCE_DATE_EPOCH` sets the timestamps (default 1980-01-01).
- `./check.sh [--roundtrip] [audit options]` builds, regenerates and diffs the CL symbol list,
  runs `epubcheck` (any fatal/error/warning fails), and runs `tools/audit.py` (internal links and
  fragments, duplicate ids, manifest, CL symbol coverage). `--require-anchors` makes a missing
  `data-symbol` anchor an error. `--roundtrip` also compares the build with `original/`
  (meaningful only on an unedited `src/`).
- `python3 -m pytest -q` runs the tool tests.

## Re-running the audits

The committed results are in `audit/text/` (EPUB vs dpANS3R text) and `audit/examples/` (the spec's
examples run in SBCL). The tools find dictionary entries by markup (`h3.entry`, recursively), so they
work on the renamed layout in `src/` and on the original flat layout (e.g. a `git archive v0-original
src/OEBPS/text` export passed as `--epub` / `--text-dir`). Results are keyed by section number and
names; file paths are reported relative to `OEBPS/`. To re-run without overwriting the committed
results, send the output elsewhere:

    python3 tools/compare_text.py --epub src/OEBPS/text --out /tmp/audit-text   # fetches dpANS3R into vendor/dpans (or pass --tex DIR)
    python3 tools/examples_run.py --text-dir src/OEBPS/text --out-dir /tmp/audit-examples

Expected: text, 3858/3917 sections at ratio 1.0 and 0 unmatched (the 25 below 1.0 since the errata
corrections are intended deviations, listed in the History note of `audit/text/summary.md`); examples,
match 2250, mismatch 114, error 145, impl-dependent 177, no-expectation 204, skipped 152, unparsed 34.
The summaries' History notes are written by hand and are not regenerated. The examples run needs
`sbcl`; some actual values (timestamps, temp paths, object addresses) differ from run to run, the
classifications do not.

## Tooling policy

Python 3 (stdlib + lxml; pytest for tests). SBCL is used only to run the spec's examples and to
list the `COMMON-LISP` external symbols. Edits to `src/` are targeted text changes, so diffs stay
reviewable.
