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
