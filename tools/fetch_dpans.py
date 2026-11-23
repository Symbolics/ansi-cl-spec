#!/usr/bin/env python3
"""Fetch dpANS3 and the dpANS3R overlay from the CMU AI Repository, verify
sha256, extract safely into vendor/dpans/, and overlay 3R onto 3 ->
vendor/dpans/merged/.  Idempotent.  The downloaded TeX is untrusted data: it is
only extracted (tarfile filter="data"), never executed."""
import hashlib
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

BASE = "https://www.cs.cmu.edu/Groups/AI/lang/lisp/doc/standard/ansi/dpans/"
FILES = {
    "dpans3.tgz": "fc230bb1d38a2bb2599f0383ede329d0d59e7cc55c36ed7336059e753c4866a0",
    "dpans3r.tgz": "8881e1fb746b882857e7e6f38acf18c50bb51df306a2f2d3aebd88ed2863d721",
}
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEST = ROOT / "vendor" / "dpans"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def download(name, dest):
    path = dest / name
    if path.exists() and sha256(path) == FILES[name]:
        return path
    print(f"downloading {name}", file=sys.stderr)
    tmp = path.with_suffix(".part")
    with urllib.request.urlopen(BASE + name, timeout=120) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f)
    got = sha256(tmp)
    if got != FILES[name]:
        tmp.unlink()
        raise SystemExit(f"sha256 mismatch for {name}: expected {FILES[name]}, got {got}")
    tmp.rename(path)
    return path


def extract(tgz, outdir):
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    with tarfile.open(tgz) as tf:
        tf.extractall(outdir, filter="data")


def fetch(dest=DEFAULT_DEST):
    """Return the path of the merged tree."""
    dest = Path(dest)
    merged = dest / "merged"
    if (merged / ".complete").exists() and all(
        (dest / n).exists() and sha256(dest / n) == h for n, h in FILES.items()
    ):
        return merged
    dest.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        download(name, dest)
    extract(dest / "dpans3.tgz", dest / "r3")
    extract(dest / "dpans3r.tgz", dest / "r3r")
    base = dest / "r3" / "dpANS3"
    over = dest / "r3r" / "dpANS3R"
    if not base.is_dir() or not over.is_dir():
        raise SystemExit("unexpected archive layout")
    if merged.exists():
        shutil.rmtree(merged)
    shutil.copytree(base, merged)
    for p in over.iterdir():
        if p.is_file():
            shutil.copy2(p, merged / p.name)
    (merged / ".complete").write_text("ok\n")
    return merged


if __name__ == "__main__":
    print(fetch(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DEST))
