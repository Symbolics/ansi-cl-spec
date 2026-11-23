#!/bin/sh
# Build, run epubcheck, audit. Extra args go to tools/audit.py (e.g. --require-anchors).
# The first arg --roundtrip additionally compares the build with original/ (only valid
# while src/ is still unmodified, i.e. before any edits).
cd "$(dirname "$0")" || exit 1
fail=0
roundtrip=0
if [ "$1" = "--roundtrip" ]; then roundtrip=1; shift; fi
mkdir -p dist

python3 tools/build.py || { echo "check: FAIL (build)"; exit 1; }

# the committed symbol list must match what SBCL reports
if command -v sbcl >/dev/null 2>&1; then
  sbcl --script tools/lisp/cl-symbols.lisp > dist/cl-symbols.txt
  if ! diff -q dist/cl-symbols.txt tools/data/cl-symbols.txt >/dev/null; then
    echo "symbol list differs from tools/data/cl-symbols.txt"; fail=1
  fi
else
  echo "note: sbcl not found, skipping symbol list check"
fi

epubcheck dist/ANSI-Common-Lisp.epub > dist/epubcheck.txt 2>&1
grep -E '^Messages:' dist/epubcheck.txt
if grep -qE '^(FATAL|ERROR|WARNING)' dist/epubcheck.txt; then
  grep -E '^(FATAL|ERROR|WARNING)' dist/epubcheck.txt | head -20
  fail=1
fi
grep -q '^EPUBCheck completed' dist/epubcheck.txt || { echo "epubcheck did not finish"; fail=1; }

python3 tools/audit.py --json dist/audit.json "$@" || fail=1
[ $roundtrip -eq 1 ] && { python3 tools/roundtrip.py || fail=1; }

if [ $fail -eq 0 ]; then echo "check: PASS"; else echo "check: FAIL"; fi
exit $fail
