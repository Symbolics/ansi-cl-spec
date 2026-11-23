# Errata and Corrections

## About this page

This edition reproduces the draft ANSI Common Lisp standard (dpANS3R) as faithfully as possible. Errors that crept in while converting the TeX source to EPUB have been corrected and are not listed individually. A small number of errors that are present in the draft itself have been corrected here as well. Every place where this edition differs from the draft text is listed below, so that a reader holding the original can find it.

Corrections were made only where the draft is clearly wrong by its own rules (other entries of the same document, or the semantics of the language), and each changed example was run in SBCL 2.6.2. Values that the draft marks implementation-dependent are left as printed.

## Corrections to the draft

Each item gives the section and entry, what the draft said, and what this edition says.

1. 3.8.12 macroexpand, macroexpand-1. Draft: `(defmacro delta ...)` returns `EPSILON`. Here: `DELTA`.
2. 3.8.15 \*macroexpand-hook\*. Draft: output `Now expanding (MACHOOK 1 2)`. Here: `Now expanding: (MACHOOK 1 2)`, matching the hook's format string.
3. 3.8.20 dynamic-extent. Draft: the example calls `string-search`, which is not a Common Lisp function. Here: `search`.
4. 5.3.4 fboundp. Draft: `(fboundp 'nth-value)` is false. Here: true, since `nth-value` is a macro and the names of macros are fbound.
5. 5.3.28 throw. Draft: the printed line and its prose omit the final period of `"The inner catch returns ~s.~%"`. Here: the period is shown.
6. 7.7.1 function-keywords. Draft: the second call examines the method of `gf1` but shows `(), false`. Here: it examines the method of `gf2`, which has no keywords.
7. 9.2.40 with-simple-restart. Draft: the example uses the non-existent `fixnump`. Here: `(typep result 'fixnum)`.
8. 9.2.40 with-simple-restart. Draft: `(or (compute-fixnum-power-of-2 x) 'something big)`, which returns `SOMETHING`. Here: `'something-big`, matching the result shown.
9. 9.2.43 muffle-warning. Draft: `(defun quiet-warning-handler ...)` returns `CUSTOM-WARNING-HANDLER`. Here: `QUIET-WARNING-HANDLER`.
10. 11.2.9 shadow. Draft: `(find-symbol 'car 'temp)`, a symbol where a string is required. Here: `(find-symbol "CAR" 'temp)` (two places).
11. 12.2.23 sinh, cosh, tanh, asinh, acosh, atanh (inverse hyperbolic sine). Draft: a number with imaginary part pi/2 is in the range "if and only if its imaginary part is non-negative". Here: "its real part is non-negative".
12. 12.2.23 sinh, cosh, tanh, asinh, acosh, atanh (inverse hyperbolic tangent). Draft: a number with imaginary part pi/2 is in the range "if and only if its imaginary part is strictly positive". Here: "its real part is strictly positive".
13. 12.2.43 \*random-state\*. Draft: `(random)` with no argument, which is an error. Here: `(random 100)`.
14. 14.2.12 subst, subst-if, subst-if-not, nsubst, nsubst-if, nsubst-if-not. Draft: `(subst-if-not '(x) #'consp tree1)` returns `(1 X)`. Here: `((X) ((X) (X) X) ((X) (X) (X) X) ((X) (X) (X) (X) X) X)`, the value the definition prescribes.
15. 14.2.43 intersection, nintersection. Draft: the lists are built with unquoted `a b c d`. Here: `'a 'b 'c 'd`.
16. 14.2.47 set-exclusive-or, nset-exclusive-or. Draft: `(list (("a" . "b") ...))`, which calls a list as a function (two places). Here: `(copy-list '(("a" . "b") ...))`.
17. 17.3.21 merge. Draft: `(copy-seq :nosy")` and `(vector ((red . 1) (blue . 4)))` (and the analogous second vector). Here: `(copy-seq "nosy")`, `(vector '(red . 1) '(blue . 4))` and `(vector '(yellow . 2) '(green . 7))`.
18. 19.4.13 wild-pathname-p. Draft: `(pathname :name "F*O")`. Here: `(make-pathname :name "F*O")`.
19. 22.4.18 \*print-case\*. Draft: `(defun test-print-case ...)` returns `TEST-PC`. Here: `TEST-PRINT-CASE`.
20. 22.4.27 \*print-readably\*. Draft: `(setf (gethash table 1) 'one)` and `(setf (gethash table 2) 'two)`, arguments reversed. Here: `(gethash 1 table)` and `(gethash 2 table)`.
21. 26.1 Glossary, I/O customization variable (Figure 26-2). Draft: `query-io*`. Here: `*query-io*`.

## Editorial corrections of typographical errors

Deliberate edits relative to the draft text:

- 5.3.34 eql: "folowing" is spelled "following".
- 7.7.27 defmethod: the syntax `keyword` `var`, which the draft typesets with no space ("keywordvar"), has a space.
- 21.2.33 with-open-stream: the duplicated "the" in "assign the the variable" is removed.

Doubled words in the draft, each reduced to one:

- 2.3.5 Valid Patterns for Tokens: "in the the keyword package".
- 4.4.4 compiled-function: "a a compiled function".
- 7.7.34 find-method: "an an error".
- 11.2.16 in-package: "Causes the the package".
- 12.2.59 parse-integer: "a a non-empty sequence".
- 14.2.11 sublis, nsublis: "structure structure".
- 14.2.45 pushnew: "part part of the element".
- 22.2.1.3 formatter: "the the formatter macro".
- 22.4.12 print-unreadable-object: "in the the angle brackets".
- 24.2.7 \*load-pathname\*, \*load-truename\*: "the the first argument".
- A.1.1 Removed Language Features: "in the the common-lisp package".
- 26.1 Glossary, copy: "to to the function random".
- 26.1 Glossary, em: "of of a letter M".
- 26.1 Glossary, safe: "where the the highest safety level".

## Known issues not corrected

- 5.3.61 defsetf. The `xy` example (long-form `defsetf` with `&key ((x x) 0) ((y y) 0)`, then `(setf (xy 'x 1) 1)`) is consistent with the draft's description, in which the place's subforms are evaluated, but SBCL rejects it ("Unknown &KEY argument"). We regard this as an implementation limitation rather than a draft error and left the text unchanged.
- 7.7.1 function-keywords. The bodies of the example methods `gf2` and `gf3` refer to variables that are not bound (`b` to `f`). This only affects compilation warnings; the methods are never called, so it was left alone.
- 14.2.43 and 14.2.47. The `nintersection` and `nset-exclusive-or` results, and the state of the argument lists afterwards, are implementation-dependent; the values printed in the draft are one possible outcome and may differ in your implementation.
- 19.4.13 wild-pathname-p. The last example's result (true, marked "Most places") depends on the implementation's treatment of wildcard characters in strings; SBCL returns false.
- 22.4.27 \*print-readably\*. In the "Implementation C" sketch the printed `#.` form leaves `ONE` and `TWO` unquoted; it is a hypothetical implementation's output and was left as in the draft.
