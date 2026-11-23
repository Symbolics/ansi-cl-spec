"""Short symbol links: generates dist/site/s/ (redirect pages, chooser pages, symbol list).

  s/<slug>.<kind>.html   one per inventory record: redirects to the record's page and anchor
  s/<slug>.html          one per symbol: the redirect when there is one record, else a chooser page
  s/index.html           alphabetical list of all symbols

Public URLs are extension-less (GitHub Pages serves /s/cadr from s/cadr.html). Targets are relative so a
local build works too.
"""
import html
import json
from pathlib import Path
from urllib.parse import quote

from . import slug as slugmod

TITLE_MAX = 60


def esc(s):
    return html.escape(s, quote=True)


def file_href(name):
    """Relative URL of a page in s/ (names contain * + = & which are legal in paths; & is escaped by esc())."""
    return quote(name, safe="*+=&-_.")


def shorten(title, n=TITLE_MAX):
    return title if len(title) <= n else title[:n - 1].rstrip(", ") + "…"


def label(rec):
    return "%s (%s, %s)" % (rec["symbol"], rec["kind"], rec["secno"])


def target(rec):
    return "../" + rec["href"]


def redirect_page(rec, site):
    t = esc(target(rec))
    canon = esc(site + rec["href"])
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\"/>\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
            "<meta name=\"robots\" content=\"noindex\"/>\n"
            "<title>%s</title>\n"
            "<meta http-equiv=\"refresh\" content=\"0; url=%s\"/>\n"
            "<link rel=\"canonical\" href=\"%s\"/>\n</head>\n<body>\n"
            "<p><a href=\"%s\">Go to %s</a></p>\n"
            "<script>location.replace(document.querySelector(\"a\").href)</script>\n"
            "</body>\n</html>\n") % (esc(rec["symbol"]), t, canon, t, esc(label(rec)))


def secno_key(rec):
    return [int(p) if p.isdigit() else 0 for p in rec["secno"].split(".")] + [rec["path"], rec["anchor"]]


def chooser_page(recs, site):
    name = recs[0]["symbol"]
    items = "\n".join(
        "<li><a href=\"%s\">%s</a>: %s %s</li>" % (
            esc(target(r)), esc(r["kind"]), esc(r["secno"]), esc(shorten(r["title"])))
        for r in sorted(recs, key=secno_key))
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\"/>\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
            "<title>%s</title>\n"
            "<link rel=\"stylesheet\" type=\"text/css\" href=\"../assets/site.css\"/>\n</head>\n<body>\n"
            "<p><a href=\"../index.html\">ANSI Common Lisp</a> · <a href=\"../nav.xhtml\">Contents</a></p>\n"
            "<h1>%s</h1>\n<p>This symbol has several meanings:</p>\n<ul>\n%s\n</ul>\n"
            "</body>\n</html>\n") % (esc(name), esc(name), items)


def index_page(by_symbol):
    lines = []
    for name in sorted(by_symbol, key=lambda n: (slugmod.slug(n), n)):
        recs = by_symbol[name]
        kinds = ", ".join(r["kind"] for r in sorted(recs, key=secno_key))
        lines.append("<li><a href=\"%s\">%s</a> (%s)</li>" % (
            esc(file_href(slugmod.slug(name) + ".html")), esc(name), esc(kinds)))
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\"/>\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
            "<title>Symbols</title>\n"
            "<link rel=\"stylesheet\" type=\"text/css\" href=\"../assets/site.css\"/>\n</head>\n<body>\n"
            "<p><a href=\"../index.html\">ANSI Common Lisp</a> · <a href=\"../nav.xhtml\">Contents</a></p>\n"
            "<h1>Symbols</h1>\n<p>%d symbols. Short links have the form <code>/s/&lt;symbol&gt;</code> and "
            "<code>/s/&lt;symbol&gt;.&lt;kind&gt;</code>.</p>\n<ul>\n%s\n</ul>\n"
            "</body>\n</html>\n") % (len(by_symbol), "\n".join(lines))


def write_short_pages(inventory_path, out, site):
    """Write out/s/. Fails on slug collisions, a record whose `short` disagrees with the rule."""
    records = json.loads(Path(inventory_path).read_text(encoding="utf-8"))["entries"]
    by_symbol = {}
    for r in records:
        by_symbol.setdefault(r["symbol"], []).append(r)
    try:
        slugmod.check_unique(by_symbol)
        seen = set()
        for r in records:
            want = slugmod.short(r["symbol"], r["kind"])
            if r.get("short") != want:
                raise ValueError("inventory short %r != %r for %r" % (r.get("short"), want, r["symbol"]))
            if want in seen:
                raise ValueError("duplicate (symbol, kind) %r" % want)
            seen.add(want)
    except ValueError as e:
        raise SystemExit("build_site: %s" % e)
    d = Path(out) / "s"
    d.mkdir()
    for r in records:
        (d / (r["short"][2:] + ".html")).write_text(redirect_page(r, site), encoding="utf-8")
    for name, recs in by_symbol.items():
        page = redirect_page(recs[0], site) if len(recs) == 1 else chooser_page(recs, site)
        (d / (slugmod.slug(name) + ".html")).write_text(page, encoding="utf-8")
    (d / "index.html").write_text(index_page(by_symbol), encoding="utf-8")
    return len(records) + len(by_symbol) + 1
