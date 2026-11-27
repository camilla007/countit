from countit.classify import classify_keysym
from countit.model import EventClass


def test_classifies_without_decoding_text():
    assert classify_keysym(ord("a")) is EventClass.PRINTABLE
    assert classify_keysym(0x0101F600) is EventClass.PRINTABLE
    assert classify_keysym(0xFF08) is EventClass.CORRECTION
    assert classify_keysym(0xFFFF) is EventClass.CORRECTION
    assert classify_keysym(0xFF51) is EventClass.NAVIGATION
    assert classify_keysym(0xFFE1) is EventClass.MODIFIER
    assert classify_keysym(0) is EventClass.OTHER


def test_control_keysyms_are_not_printable():
    for keysym in (0x1F, 0x7F, 0x80, 0x9F):
        assert classify_keysym(keysym) is EventClass.OTHER
    for keysym in (0x20, 0x7E, 0xA0, 0xFF):
        assert classify_keysym(keysym) is EventClass.PRINTABLE
