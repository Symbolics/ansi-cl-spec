#!/usr/bin/env python3
"""Validate a built site: every .xhtml parses, and every relative href/src (and meta-refresh url) resolves to a file
(and, with a fragment, to an existing id in the target); the same for every href in search.json and toc.json. Usage: python3 tools/site/check.py dist/site"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from lxml import etree

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
LINK_ATTRS = ("href", "src")
INDEX_FILES = ("search.json", "toc.json")  # JSON indexes of site-relative hrefs: items[*][2], nested toc [title, href, children]


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
        if el.tag.rpartition("}")[2] == "meta" and (el.get("http-equiv") or "").lower() == "refresh":
            m = re.search(r"url\s*=\s*(\S+)", el.get("content") or "", re.I)
            if m:
                links.append(("meta-refresh", m.group(1).strip("'\"")))
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
            if u.fragment and attr in ("href", "meta-refresh") and target.suffix in (".xhtml", ".html"):
                stats["fragments"] += 1
                t = info(target)
                if t is not None and unquote(u.fragment) not in t[0]:
                    errors.append("%s: href=%r: no id %r in %s" % (rel, val, unquote(u.fragment),
                                                                  target.relative_to(site)))
    for name in INDEX_FILES:
        f = site / name
        if f.is_file():
            check_index(site, f, info, errors, stats)
    return errors, stats


def _index_entries(name, data):
    """[(label, href)] of a JSON index."""
    if name == "toc.json":
        out, stack = [], list(reversed(data["toc"]))
        while stack:
            n = stack.pop()
            out.append((n[0], n[1]))
            if len(n) > 2:
                stack.extend(reversed(n[2]))
        return out
    return [(item[0], item[2]) for item in data["items"]]


def check_index(site, f, info, errors, stats):
    """Every href in search.json / toc.json must resolve to a file and, with a fragment, to an id in it."""
    try:
        entries = _index_entries(f.name, json.loads(f.read_text(encoding="utf-8")))
    except (ValueError, KeyError, IndexError, TypeError, OSError) as e:
        errors.append("%s: unreadable: %s" % (f.name, e))
        return
    for label, href in entries:
        u = urlsplit(href)
        stats["links"] += 1
        target = (site / unquote(u.path)).resolve()
        if u.scheme or not target.is_file() or site not in target.parents:
            errors.append("%s: href=%r (%r): no such file" % (f.name, href, label))
        elif u.fragment and target.suffix in (".xhtml", ".html"):
            stats["fragments"] += 1
            t = info(target)
            if t is not None and unquote(u.fragment) not in t[0]:
                errors.append("%s: href=%r (%r): no id %r" % (f.name, href, label, unquote(u.fragment)))


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
