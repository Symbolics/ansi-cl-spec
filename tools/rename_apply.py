#!/usr/bin/env python3
"""Apply tools/data/path-map.json: git mv every file, then rewrite href/src values.

References are rewritten by targeted text splices of attribute values only; nothing else
in any file changes. Idempotent: reports and does nothing if already applied.
"""
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OEBPS = ROOT / "src" / "OEBPS"
MAP_FILE = ROOT / "tools" / "data" / "path-map.json"

ATTR_RE = re.compile(r'(?<=\s)((?:href|src)=")([^"]*)(")')
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def rewrite_value(value, old_ref, new_ref, mapping):
    """Map one attribute value from the file at old_ref to the file at new_ref."""
    path, hash_, frag = value.partition("#")
    if not path or SCHEME_RE.match(path) or path.startswith("/"):
        return value
    target = posixpath.normpath(posixpath.join(posixpath.dirname(old_ref), path))
    target = mapping.get(target, target)
    rel = posixpath.relpath(target, posixpath.dirname(new_ref) or ".")
    return rel + hash_ + frag


def rewrite_text(text, old_ref, new_ref, mapping):
    """Return text with every href/src value re-expressed relative to new_ref."""
    return ATTR_RE.sub(lambda m: m.group(1) + rewrite_value(m.group(2), old_ref, new_ref, mapping) + m.group(3), text)


def main():
    mapping = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    moved = {o: n for o, n in mapping.items() if o != n}
    old_present = [o for o in moved if (OEBPS / o).exists()]
    new_present = [n for n in moved.values() if (OEBPS / n).exists()]
    if not old_present and len(new_present) == len(moved):
        print("rename_apply: already applied, nothing to do")
        return 0
    if old_present and new_present:
        raise SystemExit("rename_apply: tree is partially renamed; refusing to continue")

    for o, n in moved.items():
        (OEBPS / n).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", str(OEBPS / o), str(OEBPS / n)], cwd=ROOT, check=True)

    inverse = {n: o for o, n in mapping.items()}
    files = [OEBPS / "nav.xhtml", OEBPS / "toc.ncx", OEBPS / "content.opf"]
    files += [p for p in sorted((OEBPS / "text").rglob("*.xhtml"))]
    changed = 0
    for p in files:
        new_ref = p.relative_to(OEBPS).as_posix()
        old_ref = inverse.get(new_ref, new_ref)
        old = p.read_bytes().decode("utf-8")
        new = rewrite_text(old, old_ref, new_ref, mapping)
        if new != old:
            p.write_bytes(new.encode("utf-8"))
            changed += 1
    print(f"rename_apply: moved {len(moved)} files, rewrote references in {changed} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
