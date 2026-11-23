import conv_nbsp as c

SRC = ('<p>a b <code>x y</code> &#160; <pre>(f  z)\n  <b>q</b> r</pre></p>'
       '<table><tr><td> </td></tr></table>')


def test_only_code_and_pre():
    new, n = c.transform(SRC)
    assert n == 4
    assert '<code>x y</code>' in new and '<pre>(f  z)\n  <b>q</b> r</pre>' in new
    assert '<p>a b ' in new and '&#160; ' in new and '<td> </td>' in new


def test_idempotent():
    new, _ = c.transform(SRC)
    assert c.transform(new) == (new, 0)
