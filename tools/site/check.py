#!/usr/bin/env python3
"""Validate a built site: every .xhtml parses, and every relative href/src resolves to a file
(and, with a fragment, to an existing id in the target). Usage: python3 tools/site/check.py dist/site"""
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lxml import etree

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
LINK_ATTRS = ("href", "src")


def _scan(path):
    """Return (ids, [(attr, value)]) for a parsed page."""
    root = etree.parse(str(path)).getroot()
    ids, links = set(), []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        i = el.get("id") or el.get(XML_ID)
        if i:
            ids.add(i)
        for a in LINK_ATTRS:
            v = el.get(a)
            if v is not None:
                links.append((a, v))
    return ids, links


def check_site(site):
    """Return (errors, stats)."""
    site = Path(site).resolve()
    errors, cache = [], {}
    stats = {"pages": 0, "links": 0, "fragments": 0}

    def info(p):
        if p not in cache:
            try:
                cache[p] = _scan(p)
            except (etree.XMLSyntaxError, OSError) as e:
                cache[p] = None
                errors.append("%s: not well-formed: %s" % (p.relative_to(site), e))
        return cache[p]

    pages = sorted(list(site.rglob("*.xhtml")) + list(site.rglob("*.html")))
    for p in pages:
        stats["pages"] += 1
        r = info(p)
        if r is None:
            continue
        rel = p.relative_to(site)
        for attr, val in r[1]:
            u = urlsplit(val)
            if u.scheme or u.netloc:
                continue
            stats["links"] += 1
            if u.path:
                target = (p.parent / unquote(u.path)).resolve()
            else:
                target = p
            try:
                target.relative_to(site)
            except ValueError:
                errors.append("%s: %s=%r escapes the site" % (rel, attr, val))
                continue
            if not target.is_file():
                errors.append("%s: %s=%r: no such file" % (rel, attr, val))
                continue
            if u.fragment and attr == "href" and target.suffix in (".xhtml", ".html"):
                stats["fragments"] += 1
                t = info(target)
                if t is not None and unquote(u.fragment) not in t[0]:
                    errors.append("%s: href=%r: no id %r in %s" % (rel, val, unquote(u.fragment),
                                                                  target.relative_to(site)))
    return errors, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: check.py SITE_DIR", file=sys.stderr)
        return 2
    errors, stats = check_site(argv[0])
    for e in errors[:50]:
        print("ERROR", e)
    if len(errors) > 50:
        print("... and %d more" % (len(errors) - 50))
    print("site check: %s: %d pages parsed, %d relative links resolved (%d with fragments), %d errors"
          % ("FAIL" if errors else "PASS", stats["pages"], stats["links"], stats["fragments"], len(errors)))
    return 1 if errors else 0


if __name__ == "__main__":
    # run as a script: make `tools` importable is not needed, this module has no package imports
    sys.exit(main())
