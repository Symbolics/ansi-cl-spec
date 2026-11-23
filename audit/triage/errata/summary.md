# Original-erratum correction proposals: summary

Corrections file: corrections.json (36 records). Page draft: errata-page.md. Every `old` was checked to occur exactly once in its current file; applying all fixes to copies of the 33 affected files left them well-formed XML.

## Counts

- Records: 36 = 21 example/text corrections (19 numbered items on the page, where 9.2.40 and 12.2.23 each carry two edits) + 14 doubled-word fixes + 1 no-fix (5.3.61 defsetf).
- Confidence: high 32, medium 3 (E04, E11, E13), low 1 (E06, no fix).
- Plus the 3 deliberate edits, listed on the page without a fix.
- One item (E12b, arctanh) is new: not in the triage records, found while checking 12.2.23.
- Triage notes contradicted: 17.3.21 merge needs "nosy" (lower case), not "NOSY"; 2.3 "the the" is in 2.3.5, not 2.3.4; 5.3.61 is not a draft error.

## Items

| id | section | entry | confidence | fix |
|---|---|---|---|---|
| E01 | 3.8.12 | macroexpand | high | EPSILON -> DELTA |
| E02 | 3.8.15 | *macroexpand-hook* | high | add colon in output |
| E03 | 3.8.20 | dynamic-extent | high | string-search -> search |
| E04 | 5.3.4 | fboundp | medium | false -> true |
| E05 | 5.3.28 | throw | high | final period (2 edits) |
| E06 | 5.3.61 | defsetf | low | none |
| E07 | 7.7.1 | function-keywords | high | gf1 -> gf2 |
| E08a | 9.2.40 | with-simple-restart | high | fixnump -> typep |
| E08b | 9.2.40 | with-simple-restart | high | 'something big -> 'something-big |
| E09 | 9.2.43 | muffle-warning | high | result name |
| E10 | 11.2.9 | shadow | high | "CAR" (2 edits) |
| E11 | 12.2.43 | *random-state* | medium | (random 100) |
| E12a | 12.2.23 | asinh | high | imaginary -> real part |
| E12b | 12.2.23 | atanh | high | imaginary -> real part |
| E13 | 14.2.12 | subst-if-not | medium | replace stated result |
| E14 | 14.2.43 | intersection | high | quote symbols (2 edits) |
| E15 | 14.2.47 | set-exclusive-or | high | copy-list of quoted data (2 edits) |
| E16 | 17.3.21 | merge | high | "nosy", quoted pairs (3 edits) |
| E17 | 19.4.13 | wild-pathname-p | high | make-pathname |
| E18 | 22.4.18 | *print-case* | high | TEST-PRINT-CASE |
| E19 | 22.4.27 | *print-readably* | high | gethash order (2 edits) |
| E20 | 26.1 | Fig. 26-2 | high | *query-io* |
| D01-D14 | various | doubled words | high | drop duplicate |

## Low-confidence / no-fix / medium items

- E06 defsetf (low, no fix): by the draft's own text (lambda-list variables bound to temporaries holding the values of the place subforms; the printed expansion applies a `(lambda (&key ...))` to the temporaries) the example is coherent. SBCL fails even for `(setf (xy x 1) 1)`, because it matches the &key names against gensyms, so no reformulation is runnable there. Implementation limitation; recommend reclassifying as implementation-difference.
- E04 fboundp (medium): contradicts the glossary and the neighbouring examples; fix is a single word. The author may have meant some other test.
- E11 *random-state* (medium): the missing limit is inferred (100); any positive limit repairs the example. Verified in SBCL that the first two and last two lists are equal.
- E13 subst-if-not (medium): the draft's (1 X) cannot arise from the call by any reading. We replace the stated value with the certain value; the author's intended call is unknown.
- E12 asinh/atanh (high): arcsinh branch cut and SBCL values confirm "real part"; the arctanh clause was found by analogy and confirmed with (atanh #c(2d0 0d0)).
