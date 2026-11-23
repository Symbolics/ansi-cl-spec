Iterations (exact section count out of 3917; first full run used only a handful of macros):

1. v1, macro table only: 3378 exact. Dominant noise: `\code` text kept raw, `{\keyword \&key}`, `\formatOp` losing `~`, `\EQ` vs `==`, `\OV` vs `OR→`, bullets, `<no values>`.
2. Parsed `\def` sentence macros (`\Lazychecktype`, `\Thefunction`, `\oftype` ...) from setup-terms/-sections/-document/-aux; EPUB side: only links whose text starts with a number are treated as section references; table cells separated: 3598.
3. `\code...\endcode` rendered literally (no `--`/`` ` `` ligatures, `$` and `~` literal); `~` outside code is a tie; bare `&` outside code is a table column separator; `\interleave` rendered `[[ ]]`: 3679.
4. `\Vskip..!`, `\DefunMultiWithValues`/`\DefunMultiAccessorWithValues`/`\DefsetfMulti` tables, `\Figref`, `\displayN`/`\tablefigN` captions as "Figure §" (the EPUB's "Figure 3-22." is normalised the same way), chapter-vs-section wording taken from the section macro's own text: 3710.
5. `\editornote`/`\reviewer` dropped (setup-options.tex sets `\editornotesfalse`); `\idx*` index macros dropped; comments stripped (but `%` inside `\code` is literal except at line start); file-local `\def`s (`\SatisfyTest`, `\Result` ...) honoured: 3742 -> 3790.
6. Tokeniser splits `::=`, `==`, `<>[]{}|` and the arrows so spacing differences vanish; local `\def` with `\label` bodies (`\realtypespec`) expanded into sections; text after an *empty* label (`\label X:\None.`) is attached to the previous section, as TeX typesets it: 3799 -> 3824.
7. `\DocMethods`/`\Meth` special case, `\metavar` as `<<x>>`, `\CRLF` as `[Return]`, `\TVar`, superscript/subscript marks dropped, en dash folded to `--`; `\def` inside section text now honoured: 3833.

Deliberate equivalences (these hide a difference on purpose; each is a *rendering choice* of the EPUB, not a wording change):
- `\EQ` is written `==`, `\OV` `OR→`, `\NV` `NOT→` (the TeX typesets these as symbols); `\CRLF` is `[Return]`.
- `\thenextfigure` becomes "the next figure": the EPUB never prints the figure number in running text.
- Links to sections/chapters/figures are compared as a bare marker `§`, so section titles and numbers are not compared.
- `\packref{keyword}` is not upper-cased (the EPUB writes package names in lower case).

Not hidden on purpose (they show up as differences): the `↓` marker, `$`, `dummy`, `''`, editor/`[see correction below]` text.

Known normaliser limitations: Pronunciation accent macros (9 sections, compared but excluded from the lowest-ratio list); mathematical display in asin/acos/atan, sinh/cosh/tanh, floor/ffloor, phase and log (`\over`, `\sqrt`, tabs); a few `\halign`/`\settabs` tables (bit-and, boole, short-float figures); `\def` macros that use `##`; unknown macros are counted below. The comparison is whitespace-insensitive, so spacing and line breaks (including inside `<pre>`) are not compared.

Provenance (see the report that accompanies this audit): 3833 of 3917 compared sections (97.8%) have the same word sequence as dpANS3R after normalisation; every entry name, kind and (non-empty) section label sequence matches. The EPUB reproduces TeX-source quirks that a re-authored text would not have: the stray `\Shouldchecktype` sentence that TeX typesets under *Side Effects* for rplaca/rplacd (it follows an empty `\label ... :\None.`), the two mutually exclusive `\issue` variants in subtypep, `\nullabelfalse` (no "None." sections), editor notes suppressed as `\editornotesfalse` does. Its defects (lost `$`, `dummy`, `''`, `↓`, misplaced paren in `real`) are characteristic of a script converting the TeX, not of a different source text.
