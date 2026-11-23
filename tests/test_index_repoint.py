import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("s05", Path(__file__).parent.parent / "tools" / "05_index_repoint.py")
s05 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s05)

ENTRIES = {("14-conses/14.2.9-car.xhtml", "DictEntry_car_1"): {"car", "cadr"},
           ("12-numbers/12.2.15-eq.xhtml", "DictEntry_eq_2"): {"char<=", "&optional"}}

INDEX = ('<p><b>cadr</b>  <a href="../14-conses/14.2.9-car.xhtml#DictEntry_car_1">car</a>, \n'
         '<a href="../26-glossary/c.xhtml#cons">cons</a>.\n'
         '</p><p><b>char&lt;=</b>  <a href="../12-numbers/12.2.15-eq.xhtml#DictEntry_eq_2">x</a>.\n'
         '</p><p><b>zzz</b>  <a href="../14-conses/14.2.9-car.xhtml#DictEntry_car_1">car</a>.\n'
         '</p><p><b>&amp;optional</b>  <a href="../3-evaluation-and-compilation/3.4-lambda-lists.xhtml#SubSubSectio_Specifiers_f_245">S</a>.</p>')


def run(text):
    stats = {"entry": 0, "step4": 0, "other": 0, "unmatched": []}
    return s05.repoint(text, "index/c.xhtml", ENTRIES, stats), stats


def test_repoint():
    new, st = run(INDEX)
    assert '14.2.9-car.xhtml#cadr">car</a>' in new
    assert '26-glossary/c.xhtml#cons' in new
    assert '12.2.15-eq.xhtml#char%3C=">' in new
    assert '3.4-lambda-lists.xhtml#&amp;optional">S' in new
    assert 'zzz</b>  <a href="../14-conses/14.2.9-car.xhtml#DictEntry_car_1">' in new  # name not in entry: left
    assert (st["entry"], st["step4"], len(st["unmatched"])) == (2, 1, 1)
    assert run(new)[0] == new  # idempotent
