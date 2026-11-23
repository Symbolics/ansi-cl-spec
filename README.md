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

## Tooling policy

Python 3 (stdlib + lxml; pytest for tests). SBCL is used only to run the spec's examples and to
list the `COMMON-LISP` external symbols. Edits to `src/` are targeted text changes, so diffs stay
reviewable.
