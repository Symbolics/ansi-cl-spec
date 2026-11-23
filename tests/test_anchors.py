import pytest
from anchors import name_to_id, name_to_fragment, name_to_data_symbol


@pytest.mark.parametrize("name,id_,frag", [
    ("car", "car", "car"),
    ("*print-base*", "*print-base*", "*print-base*"),
    ("1+", "1+", "1+"),
    ("char<=", "char&lt;=", "char%3C="),
    ("/=", "/=", "/="),
    ("&optional", "&amp;optional", "&amp;optional"),
    ("(setf documentation)", "(setf-documentation)", "(setf-documentation)"),
    ("CAR", "car", "car"),
    ("a%b c", "a%b-c", "a%25b-c"),
])
def test_ids(name, id_, frag):
    assert name_to_id(name) == id_
    assert name_to_fragment(name) == frag


def test_data_symbol():
    assert name_to_data_symbol("(setf documentation)") == "(setf documentation)"
    assert name_to_data_symbol("char<=") == "char&lt;="
