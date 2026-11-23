import conv_relations as c

SRC = ('<p>for <i>1 &lt;=  i &lt;=  n</i>, <i>S<sub>1</sub> &lt;&gt;  S<sub>2</sub></i>, <i>m&gt;=2</i>'
       ' and <i>10<sup>n</sup></i> <i>&lt;=</i> |a|.</p>'
       '<p>Use <b>&lt;=</b>, <code>(&lt;= 1 2)</code>, <i><a href="x">&lt;=</a></i>, <pre>(>= a b)</pre> and plain &lt;= here.</p>')


def test_math_only():
    new, n = c.transform(SRC)
    assert n == 5
    assert '<i>1 ≤ i ≤ n</i>' in new
    assert '<i>S<sub>1</sub> ≠ S<sub>2</sub></i>' in new
    assert '<i>m≥2</i>' in new
    assert '<i>≤</i> |a|' in new
    # Lisp symbols untouched
    assert '<b>&lt;=</b>' in new and '<code>(&lt;= 1 2)</code>' in new and '<a href="x">&lt;=</a>' in new
    assert 'plain &lt;= here' in new and '<pre>(>= a b)</pre>' in new


def test_idempotent():
    new, _ = c.transform(SRC)
    assert c.transform(new) == (new, 0)
