import conv_eq
import conv_pi

EQ = ('<pre> (gcd x y) ==(gcd y x)\n (a) == (b) ==<i>j</i>\n(f)\n==\n(g)\n</pre><li>== \n<p>x</p>')


def test_eq():
    new, n = conv_eq.transform(EQ)
    assert n == 5
    assert '(gcd x y) ≡ (gcd y x)' in new          # lost space restored, one space
    assert '(a) ≡ (b) ≡ <i>j</i>' in new         # existing space kept; space added before markup
    assert '\n≡\n(g)' in new and '<li>≡ \n' in new   # nothing added before whitespace
    assert conv_eq.transform(new) == (new, 0)


PI = ('<p>approximation to <i> pi </i> and <i>- pi /2</i>, <i>- pi  i/2</i>, <i> ( pi /2) - x </i>.</p>'
      '<table><tr><td>0 &lt; r &lt;  pi /2 </td><td>+ pi </td><td>pi</td></tr></table>'
      '<pre>(cos pi) (float pi 0.0)</pre><p>the constant <b>pi</b> and <a href="x#pi">pi</a>, <code>(sqrt pi)</code></p>')


def test_pi():
    new, n = conv_pi.transform(PI)
    assert n == 6
    assert '<i>π</i> and <i>-π/2</i>, <i>-πi/2</i>, <i> (π/2) - x </i>.' in new
    assert '<td>0 &lt; r &lt; π/2 </td><td>+π</td><td>pi</td>' in new
    # the Lisp constant is never touched
    for keep in ('<pre>(cos pi) (float pi 0.0)</pre>', '<b>pi</b>', '<a href="x#pi">pi</a>', '<code>(sqrt pi)</code>'):
        assert keep in new
    assert conv_pi.transform(new) == (new, 0)
