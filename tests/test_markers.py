import collections
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("s06", Path(__file__).parent.parent / "tools" / "06_markers.py")
s06 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s06)

SRC = ('<h3 id="DictEntry_x_1" class="entry"><span class="secno">1.1</span> <span class="names">x</span> '
       '<span class="kind">Standard Generic Function</span></h3>\n<dl>\n<dt><b>Arguments and Values:</b></dt><dd>a</dd>'
       '<dt><b>See Also:</b></dt><dd>b</dd></dl>')


def test_markers():
    k, s = collections.Counter(), collections.Counter()
    new, nh, nd = s06.transform(SRC, k, s)
    assert (nh, nd) == (1, 2)
    assert '<h3 id="DictEntry_x_1" class="entry" data-kind="standard-generic-function"><span class="secno">' in new
    assert '<dt data-section="arguments-and-values"><b>Arguments and Values:</b></dt>' in new
    assert '<dt data-section="see-also"><b>See Also:</b></dt>' in new
    assert s06.transform(new) == (new, 0, 0)


def test_non_entry_file_untouched():
    t = "<dl><dt><b>Term:</b></dt></dl>"
    assert s06.transform(t) == (t, 0, 0)
