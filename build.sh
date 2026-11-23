#!/bin/sh
# Build dist/ANSI-Common-Lisp.epub from src/ (options: --src DIR --out FILE).
exec python3 "$(dirname "$0")/tools/build.py" "$@"
