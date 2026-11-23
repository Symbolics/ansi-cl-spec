#!/usr/bin/env python3
"""Build a deterministic EPUB from an unpacked source tree."""
import argparse
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def is_skipped(rel):
    name = rel.name
    return any(p.startswith(".") for p in rel.parts) or name.endswith(("~", ".swp", ".bak"))


def zip_date_time():
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is None:
        return (1980, 1, 1, 0, 0, 0)
    import time
    t = time.gmtime(max(int(epoch), 315532800))  # ZIP cannot go before 1980
    return (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec - t.tm_sec % 2)


def build(src, out):
    src, out = Path(src), Path(out)
    if not (src / "mimetype").is_file():
        raise SystemExit(f"build: {src}/mimetype not found")
    files = sorted(
        (p.relative_to(src) for p in src.rglob("*") if p.is_file()),
        key=lambda r: r.as_posix(),
    )
    files = [r for r in files if not is_skipped(r) and r.as_posix() != "mimetype"]
    out.parent.mkdir(parents=True, exist_ok=True)
    dt = zip_date_time()

    def info(name, method):
        zi = zipfile.ZipInfo(name, dt)
        zi.compress_type = method
        zi.external_attr = 0o644 << 16
        zi.create_system = 3
        zi.extra = b""
        return zi

    with zipfile.ZipFile(out, "w") as z:
        z.writestr(info("mimetype", zipfile.ZIP_STORED), (src / "mimetype").read_bytes())
        for rel in files:
            z.writestr(info(rel.as_posix(), zipfile.ZIP_DEFLATED), (src / rel).read_bytes(),
                       compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=str(ROOT / "src"))
    ap.add_argument("--out", default=str(ROOT / "dist" / "ANSI-Common-Lisp.epub"))
    a = ap.parse_args(argv)
    print(f"built {build(a.src, a.out)}")


if __name__ == "__main__":
    sys.exit(main())
