"""Spine and table-of-contents model for the web edition.

All page paths are POSIX paths relative to OEBPS/ (the same as inventory hrefs).
"""
import posixpath
import re
from pathlib import Path

from lxml import etree

NS = {"x": "http://www.w3.org/1999/xhtml", "o": "http://www.idpf.org/2007/opf"}
EPUB = "http://www.idpf.org/2007/ops"
NAV = "nav.xhtml"
COVER = "text/cover.xhtml"


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


class Node:
    def __init__(self, title, href, parent=None):
        self.title = title
        self.href = href  # as written in nav.xhtml, with fragment
        self.file = href.split("#", 1)[0]
        self.fragment = href.split("#", 1)[1] if "#" in href else ""
        self.parent = parent
        self.children = []

    def __repr__(self):
        return "Node(%r, %r)" % (self.title, self.href)


def parse_spine(opf_path):
    root = etree.parse(str(opf_path)).getroot()
    items = {i.get("id"): i.get("href") for i in root.iterfind(".//o:manifest/o:item", NS)}
    return [items[r.get("idref")] for r in root.iterfind(".//o:spine/o:itemref", NS)]


def parse_nav(nav_path):
    """Return the top-level Node list of the epub:type=toc nav."""
    root = etree.parse(str(nav_path)).getroot()
    nav = None
    for n in root.iter("{%s}nav" % NS["x"]):
        if n.get("{%s}type" % EPUB) == "toc":
            nav = n
            break
    if nav is None:
        raise ValueError("no <nav epub:type=\"toc\"> in %s" % nav_path)

    def walk(ol, parent):
        out = []
        for li in ol.findall("x:li", NS):
            a = li.find("x:a", NS)
            if a is None or not a.get("href"):
                continue
            node = Node(norm("".join(a.itertext())), a.get("href"), parent)
            sub = li.find("x:ol", NS)
            if sub is not None:
                node.children = walk(sub, node)
            out.append(node)
        return out

    ol = nav.find("x:ol", NS)
    return walk(ol, None) if ol is not None else []


class Toc:
    def __init__(self, spine, roots):
        self.spine = list(spine)
        self.roots = roots
        self.order = [p for p in self.spine if p != COVER]
        self.index = {p: i for i, p in enumerate(self.order)}
        self.primary = {}
        stack = list(reversed(roots))
        while stack:
            n = stack.pop()
            self.primary.setdefault(n.file, n)
            stack.extend(reversed(n.children))

    @classmethod
    def load(cls, oebps):
        oebps = Path(oebps)
        return cls(parse_spine(oebps / "content.opf"), parse_nav(oebps / NAV))

    def node(self, page):
        return self.primary.get(page)

    def prev(self, page):
        i = self.index.get(page)
        return self.order[i - 1] if i else None

    def next(self, page):
        i = self.index.get(page)
        return self.order[i + 1] if i is not None and i + 1 < len(self.order) else None

    def up(self, page):
        """File of the parent of the page's primary node; nav.xhtml for top-level nodes; None for nav.xhtml."""
        if page == NAV:
            return None
        n = self.node(page)
        if n is None:
            return NAV
        return n.parent.file if n.parent else NAV

    def ancestors(self, page):
        """Nodes from the top level down to the page's own node (empty if the page has no node)."""
        n = self.node(page)
        chain = []
        while n is not None:
            chain.append(n)
            n = n.parent
        return chain[::-1]

    def title(self, page):
        n = self.node(page)
        if n:
            return n.title
        return "Contents" if page == NAV else None


def relpath(target, page):
    """Link from `page` to `target` (both relative to OEBPS/, target may carry a fragment)."""
    path, _, frag = target.partition("#")
    rel = posixpath.relpath(path, posixpath.dirname(page) or ".")
    return rel + ("#" + frag if frag else "")


def shorten(title, limit=60):
    """Long titles become 'secno first-name …'. Returns (text, shortened?)."""
    if len(title) <= limit:
        return title, False
    m = re.match(r"^(\S*\d\S*)\s+(.*)$", title)
    num, rest = (m.group(1) + " ", m.group(2)) if m else ("", title)
    first = rest.split(",")[0].split(" — ")[0].strip()
    if len(num + first) > limit:
        first = first[: max(1, limit - len(num))].rsplit(" ", 1)[0].rstrip(",;:") or first[:limit]
    return (num + first + " …"), True
