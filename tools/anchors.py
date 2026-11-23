"""Shared helpers for per-symbol anchors: name -> id, name -> href fragment.

The id is the symbol name as printed, lowercased; `(setf x)` becomes `(setf-x)` because ids
may not contain spaces. Attribute values are XML-escaped; href fragments are additionally
percent-encoded so they are URL-safe.
"""
import re
from urllib.parse import quote

# characters left unescaped in a fragment (RFC 3986 fragment chars, minus '#')
_FRAGMENT_SAFE = "!$&'()*+,/:;=?@-._~"


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def xml_unescape(s):
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
            .replace("&apos;", "'").replace("&amp;", "&"))


def raw_id(name):
    """Unescaped id for NAME (a plain, unescaped symbol name)."""
    n = name.strip().lower()
    m = re.fullmatch(r"\(setf\s+(.+)\)", n)
    if m:
        n = "(setf-" + m.group(1).strip() + ")"
    return re.sub(r"\s+", "-", n)


def name_to_id(name):
    """Value to write inside id="..." (XML-escaped)."""
    return xml_escape(raw_id(name))


def name_to_data_symbol(name):
    """Value to write inside data-symbol="..." (name as printed, XML-escaped)."""
    return xml_escape(name.strip())


def name_to_fragment(name):
    """Fragment (without '#') to write inside href="..." (URL-safe, XML-escaped)."""
    return xml_escape(quote(raw_id(name), safe=_FRAGMENT_SAFE))
