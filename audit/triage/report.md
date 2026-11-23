# Fidelity triage: consolidated report (2026-11-23)

Inputs:
- the example audit (`audit/examples/`: SBCL 2.6.2, 3,014 steps);
- the dictionary text audit against dpANS3R (`audit/text/`: 3,917 sections, 97.8% word-identical);
- six per-chapter triage agents (g1–g6) and a book-wide sweep (pattern search plus a comparison of the concept sections and glossary: 729 sections, 691 glossary entries).

Every item was checked against the EPUB and the TeX by eye. The orchestrator re-checked a sample of verdicts against the sources:
- `''` → `"` in quote;
- dummy loss in flet;
- `real` brackets;
- `sbit`;
- `#\/`;
- `↓` via `\stardown`;
- the `documentation` structure-class methods;
- `SYS$DISK`;
- the `arctan` formula;
- the `defclass` `·`;
- the `merge` erratum;
- the glossary `\gexample` quotes and the book's straight-quote convention;
- the format-directive tildes;
- the 3.4 BNF;
- the `char-name` NBSP.

Where agents disagreed (the sweep said `SYS$DISK` is intact; g5 said it is garbled), the orchestrator checked the file: g5 is right.

## Counts (675 item records)

| category | records | action |
|---|---|---|
| conversion-error | 231 | **199 fixes** in 81 files (`fixes.json`); the other records share a fix |
| original-erratum | 38 | none (policy decision) |
| deliberate-edit | 3 | none (policy decision) |
| implementation-difference | 115 | none (SBCL behaviour) |
| harness-limitation | 170 | none |
| normaliser-noise | 111 | none (checked by eye) |
| uncertain | 7 | the ASCII math-relation convention (below) |

Dry run: all 199 fixes apply to the current `main` tree. Each `old` is unique in its file, none overlap, and every patched file is well-formed XML.

## Conversion errors by kind

- **Glossary example quotes lost** (93 fixes): `\gexample{…}` = `` ``…'' ``; restored as straight `"…"`, the book's convention.
- **`↓` lost in `{↓x}*` BNF** (\stardown): case/ccase/ecase, typecase, cond, setq/psetq, setf/psetf, loop, defgeneric, defstruct, handler-bind/case, define-condition, restart-bind, defpackage; also in 1.4.1.2.3.
- **`''` → `"` in code**: quote, defmacro (unbalanced string, which breaks the later examples), macro-function, constantp, get, and 2.4.3.1.
- **"dummy" dropped**: flet/labels, let, catch, return-from (`(return-from temp ')`), unwind-protect, subtypep (`(satisfies )`).
- **`$` taken as math**: `SYS$DISK` (make-pathname, logical-pathname-translations), `|#$-reader|` (set-dispatch-macro-character), stray `$|$` in the define-compiler-macro/defmacro Syntax, raw `var$<sub>i</sub>$` in dynamic-extent.
- **Formulas**: acos (`i (sqrt(1−z)/2)` → `i sqrt((1−z)/2)`) and arctan (lost grouping over 2i); `*-epsilon` (ε, italic spill).
- **BNF and brackets**: `(real [lower-limit [upper-limit]])` in real/float/rational/integer; lambda-list BNF in 3.4.3–3.4.5 (missing `}`, `*`, misplaced `]`, lost `{var | ↓lambda-list}`); `defclass` (`·` → `.`, "slot name" → `slot-name`).
- **Syntax and signatures**: sbit `→ bit` (was `new-bit`), `subscrips` → `subscripts`; `documentation` lost all `structure-class` methods (duplicate `standard-class` lines), and 19 instances of `new value` → `new-value`.
- **Cross-references**: "Chapter 9 (Conditions)" reduced to a bare "Conditions" in type-error-datum, package-error, file-error-pathname, stream-error-stream, print-not-readable-object.
- **Characters and code**: `#\/` → `#\ ` (read), `#\α` → `#\\alfa` (alpha-char-p), `#\` + NBSP (char-name), tildes in format directives (22.3.7.4, 22.3.3.3), hyphen rulers in code (boole, 22.1.3.3.2.1, 23.1.2.1, the load banner), `_` → `-` (2.3.1.1.2), literal `---` in table cells (2.3.1, 3.2.3.1).
- **Figures**: Figure 2-8 (empty `:` cell, swapped `[` `]` rows).
- **Inserted text**: "[see correction below]" in position (not in the draft). "Initialisation" → "Initialization" (7.1.4 table).
- **Minor**: adjoin (`\SatisfyTest` serial comma and italics).

## Original errata (the EPUB faithfully reproduces the draft): decision needed

About 25 distinct issues, including:
- 3.8.12 `defmacro delta … → EPSILON`;
- 3.8.15 missing colon in the expected output;
- 3.8.20 and 9.2.40 use non-CL functions (`string-search`, `fixnump`);
- 5.3.4 `(fboundp 'nth-value)` → false;
- 5.3.28 missing period;
- 5.3.61 defsetf `xy` keyword quoting;
- 7.7.1 function-keywords result;
- 9.2.43 `CUSTOM-WARNING-HANDLER` vs `quiet-warning-handler`;
- 11.2.9 `find-symbol` given a symbol;
- 12.2.43 `(random)` with no limit;
- 14.2.12, 14.2.43, 14.2.47 example slips;
- 17.3.21 merge `(copy-seq :nosy")`;
- 19.4.13 `pathname` for `make-pathname`;
- 22.4.18 `TEST-PC`;
- 22.4.27 gethash argument order;
- Figure 26-2 `query-io*`;
- doubled "the the" (2.3.4, 22.2.1.3, A.1.1, glossary *em*, *safe*);
- 12.2.23 arcsinh "imaginary part" (probably "real part").

See `groups/*.json`, category `original-erratum`.

## Deliberate edits (the EPUB already deviates from the draft): decision needed

- 5.3.34 "folowing" → "following".
- 7.7.27 "keywordvar" → "keyword var".
- 21.2.33 duplicate "the" removed.

## Conventions: decision needed

1. ≤ and ≠ are rendered as ASCII `<=`/`<>` in 1.4.1.2.1, 4.3.1, 4.3.5.1, 7.6.3, 7.6.6.4 and the glossary "bounding index", while ≥, ∈ and ⋃ appear as Unicode elsewhere.
2. 72 NBSPs inside `<pre>`/`<code>` (faithful renderings of TeX `\ `). They look like spaces but break code that is copied and pasted.
3. ≡ is rendered `==` (164 times, sometimes without a following space), and π as the italic word "pi". Both are consistent ASCII renderings; the HyperSpec also uses `==`.
