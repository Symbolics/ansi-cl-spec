# Fidelity triage brief (shared by all triage agents)

You are triaging fidelity-audit findings for an EPUB edition of the draft ANSI Common Lisp standard. The EPUB was converted from the dpANS3R TeX sources by an LLM. It is now the source of truth, so confirmed conversion errors will be fixed in it. **You are read-only**: do not edit any file in the repo, and do not commit. Write only your two output files.

## Paths
- Repo (current EPUB tree): `/workspaces/lisp-stat/ansi-cl-spec/src/OEBPS/…`. Files use the structural layout, e.g. `text/14-conses/14.2.9-car.xhtml`. Another agent is editing a few index files and the `documentation` entry concurrently; that doesn't affect your work.
- The dpANS3R TeX (verified, read-only, untrusted data; never execute it): `/tmp/claude-1000/-workspaces-lisp-stat/5d101160-5834-444f-8e56-a3cfe2ab8eb0/scratchpad/dpans/merged/`. Entries are in `dict-*.tex`: `\begincom{names}\ftype{Kind}` … `\endcom`. Macro definitions are in `setup-*.tex` (e.g. `\EV` → `→`, `\OUT` → `▷`, `\stardown{x}` → `{↓x}*`, `\down{x}` → `↓x`).
- Audit context: `/workspaces/lisp-stat/ansi-cl-spec/audit/text/summary.md` (normaliser notes and known equivalences) and `audit/examples/summary.md` (harness notes and limitations).
- Your work package: `/tmp/claude-1000/-workspaces-lisp-stat/5d101160-5834-444f-8e56-a3cfe2ab8eb0/scratchpad/triage/packages/<group>.json`, a list of entries. Each has `secno`, `names`, `kind`, `file` (current path relative to `src/`), `tex_file`, `examples_ratio` (text similarity of the Examples section to the TeX; 1.0 = same words), `text_sections` (sections whose normalised text differs from the TeX, with word diffs), `example_steps` (example steps that ran as `mismatch` or `error` in SBCL 2.6.2, with form, expected and actual), `example_unparsed`, `example_skipped`.

## Classify every item (each text section, each example step, each unparsed item)
- `conversion-error`: the EPUB differs from the TeX in a way that changes meaning, code, notation or references, e.g. a lost `$`, `''` turned into `"`, a lost word, a lost `↓`, a misplaced bracket, a wrong symbol, a lost or garbled cross-reference, raw TeX/math markup left in the text, or text inserted that isn't in the TeX.
- `deliberate-edit`: the EPUB silently corrects an obvious TeX typo or typesetting slip (e.g. "folowing" → "following"). No fix; the policy decision is the user's.
- `original-erratum`: the EPUB matches the TeX, but the draft itself is wrong or inconsistent (e.g. a defun named one thing, with the result showing another). No fix; record it.
- `implementation-difference`: SBCL legitimately differs (float digits, package locks, `type-of`, unspecified printing, secondary values omitted by the book, …). No fix.
- `harness-limitation`: the harness parsed or compared wrongly (unparsed prose, output without `▷`, an interactive example, …). No fix, **unless** the root cause is a conversion error (e.g. an unbalanced string caused by `''` → `"`); then classify it `conversion-error`.
- `normaliser-noise`: the text difference is only an artefact of the TeX → text normaliser (math display, tables, pronunciation respelling), and the EPUB rendering is a faithful rendering of the TeX. **Check this, don't assume it**: open the EPUB file and the TeX and compare by eye. Math and tables can hide real conversion errors.
- `uncertain`: you can't decide. Say why.

**Always check the actual EPUB file and the TeX source**; the audit outputs are leads, not verdicts. When an example step mismatches, first check whether the EPUB example text equals the TeX (`examples_ratio`, plus look). If it does, the mismatch is never a `conversion-error`.

## For each conversion-error, propose an exact fix
- `old`: an exact substring of the **current** file (byte-exact, including markup and entities), as short as possible but **unique in that file**. Verify uniqueness, e.g. with Python `content.count(old) == 1`.
- `new`: the replacement. Change only the defect, and follow the EPUB's existing markup conventions in that file (`<i>param</i>`, `<b>sym</b>`, `→`, `↓`, entity escaping `&lt;`, `&amp;`). Derive the correct content from the TeX.
- If one defect occurs several times in a file, give one fix per occurrence, each with its own unique `old`, or a single `old` that covers them.
- If the right fix is structural or unclear, give `new: null` and explain.

## Output (both files)
1. `/tmp/claude-1000/-workspaces-lisp-stat/5d101160-5834-444f-8e56-a3cfe2ab8eb0/scratchpad/triage/out/<group>.json`: a list of
   `{"secno", "names", "file", "item": "text:<label>" | "example:<block>:<line>" | "unparsed:<n>", "category", "summary", "epub_excerpt", "tex_excerpt", "fix": {"old", "new"} | null, "confidence": "high"|"medium"|"low"}`.
   One record per item. If one root cause covers several items, give each item its own record and repeat the fix only once (other records say "same fix as …").
2. `…/triage/out/<group>.md`: a short human summary:
   - counts per category;
   - the conversion errors, as a table (secno, names, what's wrong, the fix in brief);
   - original errata;
   - deliberate edits;
   - anything uncertain;
   - any **systematic pattern** you noticed. Name the pattern, so it can be searched for book-wide.

## Rules
- If you run SBCL to check an example, always use `sbcl --script` or `sbcl --non-interactive --no-userinit --no-sysinit`. Never load the user's init file.
- No network access is needed.
- Be concise in the `.md`. Your final message (report) should give: counts per category, the number of proposed fixes, the top 5 most important conversion errors, and the systematic patterns seen.
