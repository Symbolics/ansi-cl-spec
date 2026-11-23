# Book-wide sweep (non-dictionary text + systematic patterns)

Scripts: `/tmp/claude-1000/-workspaces-lisp-stat/5d101160-5834-444f-8e56-a3cfe2ab8eb0/scratchpad/sweep-scripts/` (`concept_cmp.py`, `compare_main.py`, `gloss.py`, `gloss_fix.py`, `fixes.py`, `build.py`). Records: `/tmp/claude-1000/-workspaces-lisp-stat/5d101160-5834-444f-8e56-a3cfe2ab8eb0/scratchpad/triage/out/sweep.json` (247 records; 17 are per-pattern roll-ups flagged `"rollup": true`).

## B. Concept-section comparison

Method: each `chap-*.tex` is flattened (`\input` expanded, comments stripped, dictionary `\begincom..\endcom` removed) and cut at every `\begin(Section|subSection|Subsection|subsection|subsubsection|subsubsubsection...)`. EPUB files without `h3.entry` are cut at every h1-h6. Heading sequences were aligned by title: 729 section/subsection segments matched (all titles identical after normalisation; the only unmatched headings are the 25 "The X Dictionary" lines that the TeX generates via `\includeDictionary`). Text compared with `tex_to_text` (+ `\DefineSection`, `\end..`, `\includeDictionary` stripped, same-file section anchors treated as §). The glossary (`concept-glossary.tex`, 691 entries) was compared entry by entry (`\gentry` vs `dt/dd`). Front matter (`legal.xhtml`), the index, and `chap-0` have no counterpart text and were not compared.

| ratio | sections/subsections (729) | glossary entries (691) |
|---|---|---|
| = 1.0 | 642 | 609 |
| 0.99-<1.0 | 27 | 6 |
| 0.98-0.99 | 24 | 23 |
| 0.95-0.98 | 18 | 45 |
| 0.90-0.95 | 11 | 6 |
| 0.80-0.90 | 4 | 2 |
| 0.50-0.80 | 2 | 0 |
| < 0.50 | 1 | 0 |

After checking every segment below 1.0 by eye against the TeX: 87 sections + 82 glossary entries differ. They break down as
- **conversion errors**: 14 sections (listed below) plus the glossary quote loss (93 example sentences in the 82 differing entries and the intro);
- **normaliser noise**: the remaining ~73 sections, mostly `\Vskip`/`\halign`/`\idx` layout macros rendered as text, figure captions and `\Figref`, same-file section links compared as words, `$C\sub{to}$` math, `\minussign`/ties; and 8 glossary entries (pronunciation respelling, one `\showthree` caption);
- **uncertain** (policy): ASCII relations in math (`<=`, `<>`) in 5 sections + glossary "bounding index".

### 40 lowest-ratio sections (triaged; all other sub-1.0 sections are in the JSON)
| secno | title | ratio | verdict |
|---|---|---|---|
| 26.1 | Glossary | 0.030 | segment = whole glossary; intro example lost quotes (fix) |
| A.1.7 | Packages No Longer Required | 0.700 | noise (\packref index macros) |
| 2.3.1 | Numbers as Tokens | 0.704 | conversion-error (--- literal x6) + noise |
| 2.4.3.1 | Examples of Single-Quote | 0.812 | conversion-error (''foo) |
| 11.1.2.2 | The COMMON-LISP-USER Package | 0.828 | noise (index macros) |
| 2.1.4.2 | Constituent Traits | 0.853 | conversion-error (":" lost; [ ] swapped) |
| 3.2.3.1 | Processing of Top Level Forms | 0.897 | conversion-error (--- cells) |
| 7.2.1 | Modifying the Structure of the Instance | 0.901 | noise (C_to/C_from) |
| 3.4.1.3 | A specifier for a rest parameter | 0.903 | noise (\idxkeyref) |
| 3.4.7 | Defsetf Lambda Lists | 0.915 | noise (\xparen) |
| 4.2.1 | Data Type Definition | 0.936 | noise |
| 12.1.5.4 | Principal Values and Branch Cuts | 0.939 | noise (quadrant figure layout) |
| 3.4.4 | Macro Lambda Lists | 0.940 | conversion-error (reqvars *, restvar ], spacing) |
| 3.4.5 | Destructuring Lambda Lists | 0.941 | conversion-error (optvars/keyvars inner choice; & allow-other-keys split) |
| 4.3 | Classes | 0.944 | normaliser-noise |
| 11.1.2.1 | The COMMON-LISP Package | 0.948 | normaliser-noise |
| 3.1.1.4 | Environment Objects | 0.948 | normaliser-noise |
| 2.1.4 | Character Syntax Types | 0.950 | normaliser-noise |
| 19.2.2.1.2 | Case in Pathname Components | 0.952 | normaliser-noise |
| 11.1.2.3 | The KEYWORD Package | 0.954 | normaliser-noise |
| 3.4.3 | Specialized Lambda Lists | 0.956 | conversion-error (missing }) |
| 22.3.7.4 | Tilde Left-Brace: Iteration | 0.958 | conversion-error (~ lost before }) |
| 22.3.1.3 | Tilde Ampersand: Fresh-Line | 0.959 | normaliser-noise |
| 6.1.1.2 | Loop Keywords | 0.961 | normaliser-noise |
| 22.1.3.3 | Printing Symbols | 0.961 | normaliser-noise |
| 21.1.1.1.1 | Input, Output, and Bidirectional Streams | 0.964 | normaliser-noise |
| 3.4.1.5 | Specifiers for &aux variables | 0.966 | normaliser-noise |
| 7.2 | Changing the Class of an Instance | 0.971 | normaliser-noise |
| 3.4.1.2 | Specifiers for optional parameters | 0.971 | normaliser-noise |
| 2.3.1.1.2 | Examples of Potential Numbers | 0.974 | conversion-error (_ -> -) |
| 3.4.2 | Generic Function Lambda Lists | 0.974 | normaliser-noise |
| 21.1.3 | Stream Arguments to Standardized Functions | 0.976 | normaliser-noise |
| 2.1.3 | Standard Characters | 0.977 | normaliser-noise |
| 1.4.1.1 | Font Key | 0.978 | normaliser-noise |
| 17.1 | Sequence Concepts | 0.979 | normaliser-noise |
| 21.1.2 | Stream Variables | 0.979 | normaliser-noise |
| 22.2.1.1 | Dynamic Control of the Arrangement of Outp | 0.981 | normaliser-noise |
| 4.3.5.1 | Topological Sorting | 0.981 | noise + math ASCII (uncertain) |
| 4.2.3 | Type Specifiers | 0.981 | normaliser-noise |
| 23.1.2.1 | Examples of Effect of Readtable Case on th | 0.982 | conversion-error (hyphen ruler) |

## Conversion errors found (all with exact fixes in `sweep.json`; 127 fixes: 34 + 93 glossary)

| secno | what is wrong | fix |
|---|---|---|
| 1.4.1.2.3 | `\stardown{normal-clause}` shows `{normal-clause}*`, arrow lost (case, ccase, ecase) | `{↓<i>normal-clause</i>}*` x3 |
| 2.4.3.1 | `''foo` (two apostrophes) rendered `"foo` x2 | restore `''foo` |
| 2.1.4.2 | Figure 2-8: `:` cell of the package-marker row is empty; `[` and `]` rows swapped (TeX: `[` opposite U,u; `]` opposite W,w) | 3 fixes |
| 2.3.1.1.2 | Figure 2-11: `\f{\_}` rendered `-` | `_` |
| 2.3.1 | `---` (TeX em dash) left literal in the Figure 2-9 legend (6 lines) | `—` |
| 3.2.3.1 | same in Figure 3-7 (9 cells) | `—` |
| 3.4.3 | `{var | (var [specializer])}*`: closing `}` missing | add `<code>}</code>` |
| 3.4.4 | `reqvars` lacks `*`; `restvar` has its `]` before `{var | ↓pattern}`; `pattern` production has run-together `↓wholevar↓reqvars...` | 3 fixes |
| 3.4.5 | `optvars`/`keyvars` lost the local `\TVar` = `{var | ↓lambda-list}`; `&allow-other-keys` split by a newline (`& allow-other-keys`) | 2 fixes |
| 7.1.4 | "Initialisation Argument List" (TeX: Initialization) | spelling |
| 22.3.7.4 | `~{str }`, `~:{str }`, `~@{str }`, `~:@{str }`: the tilde before the closing brace became U+00A0 (7 sites, 4 fixes) | restore `~}` |
| 22.3.3.3 | `F<NBSP>ee@T` should be `F~ee@T` | restore `~` |
| 22.1.3.3.2.1, 23.1.2.1 | rulers of 50/35/37 hyphens have their last 3 hyphens replaced by ` - ` (4 lines) | restore hyphens |
| 12.2.60 boole (dictionary) | same hyphen-run mangling in format string and printed header (2 lines) | restore `---Op-------Decimal-----Binary----Bits---` |
| 26.1 glossary | all 92 `\gexample` sentences + the intro example lost their quotation marks (`{``#1''}` in TeX) | 93 fixes, one per example |

## Original errata (EPUB equals TeX)
- Glossary Figure 26-2: `query-io*` (should be `*query-io*`), same in TeX.
- Doubled words reproduced from TeX: "the the" in 2.3.4 (`the \thepackage{keyword}`), 22.2.1.3 (`the \themacro{formatter}`), A.1.1 (`the \thepackage{common-lisp}`); "of of" (glossary *em*), "the the" (glossary *safe*); ~8 dictionary entries (in-package, load-pathname, print-unreadable-object, parse-integer "a a", compiled-function "a a", find-method "an an", ...).

## A. Per-pattern table (non-dictionary text; dictionary counts for reference)

| pattern | TeX occurrences (non-dict) | correct | defective | unmapped | dictionary (leads) |
|---|---|---|---|---|---|
| 1 `''` in code | 2 | 0 | 2 (2.4.3.1) | 0 | 6 code sites; audit flags 4 entries |
| 2 `$` / `\$` | 23 `\$`, 0 bare `$` in code | 23 | 0, no stray `$` | 0 | 5 + 27 sites; audit flags 11 entries |
| 3 "dummy" | 0 | - | - | - | 31 lines (let, flet, unwind-protect, catch); still defective in EPUB |
| 4 `↓` | 65 | 62 | 3 (1.4.1.2.3) | 0 | 92 sites; audit flags 14 entries |
| 5 raw math | ~655 chunks | all (no `$`, `^{`, `_{` residue) | 0 raw; ASCII `<=`/`<>` in 5 sections (policy) | 0 | `$|$` (3.8.9/3.8.10), `var$i$` (3.8.20) remain |
| 6 `#\/`, `\alfa` | 0 (about 100 `#\\x` forms all correct) | - | - | - | 5 lines; 13.2.8 `#\\alfa` remains |
| 7 chapter refs | 12 | 12 | 0 | 0 | 11 TeX; audit flags 5 entries |
| 8 BNF brackets | all BNFs in 1.4, 2.3, 3.4, 19.3 | most | 2 misplaced/missing (3.4.3, 3.4.4) + 3 related (reqvars `*`, 3.4.5 inner choices) | 0 | agents have `real` |

EPUB residue greps (all .xhtml except `index/`): `$` 45 lines (45 legitimate or dictionary leads), `\` 10 (leads: alfa, `\\DAD`, `"#\\A"` are correct Lisp strings), `^{`/`_{`/`\begin`/`\term`/`{}` 0, `-function`/`'-` 12 (all `dummy` leads), `<i></i>` 33 (dictionary syntax lines, empty italics, harmless), literal `---` 15 cells + 6 mangled hyphen lines (above). Note: `SYS$DISK:` is intact in the current 19.4.x entries.

## New systematic patterns
1. **glossary-example-quotes** (93).
2. **tilde-tie-before-closing-brace**: `~` before `\}`/`\rbr` inside prose `\f{}` became NBSP (8 sites).
3. **em-dash-literal**: `---` kept literally in table cells (15).
4. **hyphen-run-mangled**: trailing `---` of hyphen rulers turned into ` - ` (6 lines; 5 in non-dictionary).
5. **figure-cell-loss/swap** (2.1.4.2, 2.3.1.1.2).
6. **local-macro-ignored-in-bnf** (3.4.4/3.4.5 `\TVar`, `\star`).
7. **math-ascii-relations** (uncertain): `\leq`/`\neq` rendered `<=`/`<>` in 1.4.1.2.1, 4.3.1, 4.3.5.1, 7.6.3, 7.6.6.4, glossary *bounding index* but as ≥ ∈ ⋃ in 4.3.5/4.3.5.1.
8. NBSP from `\ ` (control space) is faithful; only the `~` cases above are defects (all NBSPs inside `<code>/<pre>` were inspected).

## Counts
Records 247 (230 items + 17 roll-ups): conversion-error 143, normaliser-noise 75, uncertain 6, original-erratum 6. **Proposed fixes: 127** (34 non-glossary, of which 2 in the dictionary entry `boole`; 93 glossary quotes), across 31 files; every `old` is unique in its file, no two fixes overlap, and all 31 patched files still parse as XML.
