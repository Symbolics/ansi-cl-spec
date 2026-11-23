"""Short-link slugs (a permanent public contract; see README "Short symbol links").

slug(name): lower case; a-z 0-9 - * + = & are kept; / -> _sl, < -> _lt, > -> _gt;
(setf x) -> setf-<slug(x)>. Any other character is an error. `_` never occurs in CL names, so the
rule is unambiguous. Imported by tools/09_inventory.py and the site build.
"""
import re

KEEP = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-*+=&")
REPLACE = {"/": "_sl", "<": "_lt", ">": "_gt"}


def _slug1(name):
    out = []
    for ch in name.lower():
        if ch in KEEP:
            out.append(ch)
        elif ch in REPLACE:
            out.append(REPLACE[ch])
        else:
            raise ValueError("slug: unsupported character %r in symbol %r" % (ch, name))
    return "".join(out)


def slug(name):
    m = re.fullmatch(r"\(setf\s+(.+)\)", name)
    s = "setf-" + _slug1(m.group(1)) if m else _slug1(name)
    if not s or s == "setf-":
        raise ValueError("slug: empty slug for symbol %r" % name)
    return s


def short(name, kind):
    """Site-relative, extension-less, not URL-encoded path of the precise short link."""
    return "s/%s.%s" % (slug(name), kind)


def check_unique(names):
    """Raise ValueError if two different symbols share a slug (or a slug is 'index', reserved for s/index.html)."""
    seen = {}
    for n in sorted(set(names)):
        s = slug(n)
        if s == "index":
            raise ValueError("slug: symbol %r would collide with s/index.html" % n)
        if s in seen:
            raise ValueError("slug: symbols %r and %r both map to %r" % (seen[s], n, s))
        seen[s] = n
    return seen
