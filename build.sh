#!/bin/sh
# Build dist/ANSI-Common-Lisp.epub from src/ (options: --src DIR --out FILE), then
# dist/inventory.json and dist/inventory.LICENSE (the symbol inventory, MS-PL).
d="$(dirname "$0")"
python3 "$d/tools/build.py" "$@" || exit 1
python3 "$d/tools/09_inventory.py"
