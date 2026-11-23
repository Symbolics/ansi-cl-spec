"""Splice site navigation (head links, header, breadcrumbs, pager, notice) into XHTML pages as text."""
import html
import re

from .toc import NAV, COVER, relpath, shorten

ASSET_CSS = "assets/site.css"
LEGAL = "text/front/legal.xhtml#legal-title"
BODY_OPEN = re.compile(r"<body(?:\s[^>]*)?>")


def esc(s):
    return html.escape(s, quote=True)


def label(title):
    """(escaped text, title attribute or '') for a possibly shortened title."""
    text, cut = shorten(title)
    return esc(text), (' title="%s"' % esc(title) if cut else "")


def head_html(toc, page):
    out = ['<meta name="viewport" content="width=device-width, initial-scale=1"/>',
           '<link rel="stylesheet" type="text/css" href="%s"/>' % relpath(ASSET_CSS, page)]
    if page != COVER:
        for rel, target in (("prev", toc.prev(page)), ("next", toc.next(page)), ("up", toc.up(page))):
            if target:
                out.append('<link rel="%s" href="%s"/>' % (rel, esc(relpath(target, page))))
    return "\n".join(out) + "\n"


def header_html(toc, page, edition_title):
    h = ['<header class="site-header">',
         '<a class="site-title" href="%s">%s</a>' % (relpath("index.html", page), esc(edition_title)),
         '<a class="site-contents" href="%s">Contents</a>' % relpath(NAV, page)]
    if page != COVER:
        h.append(crumbs_html(toc, page))
    h.append("</header>")
    return "\n".join(h) + "\n"


def crumbs_html(toc, page):
    items = []
    chain = toc.ancestors(page)
    if page == NAV or not chain:
        items.append('<li><span aria-current="page">Contents</span></li>')
    else:
        items.append('<li><a href="%s">Contents</a></li>' % relpath(NAV, page))
        for i, n in enumerate(chain):
            text, tip = label(n.title)
            if i == len(chain) - 1:
                items.append('<li><span aria-current="page"%s>%s</span></li>' % (tip, text))
            else:
                items.append('<li><a href="%s"%s>%s</a></li>' % (esc(relpath(n.href, page)), tip, text))
    return '<nav class="site-crumbs" aria-label="Breadcrumb"><ol>%s</ol></nav>' % "".join(items)


def pager_html(toc, page):
    parts = []
    for cls, arrow, target in (("site-prev", "←", toc.prev(page)),
                               ("site-up", "↑", toc.up(page)),
                               ("site-next", "→", toc.next(page))):
        if not target:
            continue
        text, tip = label(toc.title(target) or target)
        body = ("%s %s" % (arrow, text)) if cls != "site-next" else ("%s %s" % (text, arrow))
        parts.append('<a class="%s" href="%s"%s>%s</a>' % (cls, esc(relpath(target, page)), tip, body))
    nav = ""
    if parts:
        nav = '<nav class="site-pager" aria-label="Pages">%s</nav>\n' % "\n".join(parts)
    return nav + ('<p class="site-notice">Copyright © 2026 Symbolics Pte Ltd; this edition is distributed by '
                  'permission. See <a href="%s">Copyright and Use</a>.</p>\n' % esc(relpath(LEGAL, page)))


def add_chrome(text, toc, page, edition_title):
    """Return `text` (the page's XHTML) with the chrome spliced in."""
    m = BODY_OPEN.search(text)
    i_head = text.find("</head>")
    i_body = text.rfind("</body>")
    if not m or i_head < 0 or i_body < 0:
        raise ValueError("%s: cannot find <head>/<body> to splice into" % page)
    pager = "" if page == COVER else pager_html(toc, page)
    return (text[:i_head] + head_html(toc, page) + text[i_head:m.end()] + "\n"
            + header_html(toc, page, edition_title) + text[m.end():i_body] + pager + text[i_body:])

