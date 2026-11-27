from __future__ import annotations

from .model import EventClass

# X11 keysym groups. The collector sees a keycode only long enough to map it here.
CORRECTION = {0xFF08, 0xFFFF}  # BackSpace, Delete
NAVIGATION = {0xFF50, 0xFF51, 0xFF52, 0xFF53, 0xFF54, 0xFF55, 0xFF56, 0xFF57, 0xFF63}
MODIFIERS = {
    0xFFE1,
    0xFFE2,
    0xFFE3,
    0xFFE4,
    0xFFE5,
    0xFFE6,
    0xFFE7,
    0xFFE8,
    0xFFE9,
    0xFFEA,
    0xFFEB,
    0xFFEC,
}


def classify_keysym(keysym: int) -> EventClass:
    """Classify without returning or retaining actual key identity."""
    if keysym in CORRECTION:
        return EventClass.CORRECTION
    if keysym in NAVIGATION:
        return EventClass.NAVIGATION
    if keysym in MODIFIERS:
        return EventClass.MODIFIER
    # Printable Latin-1 and Unicode keysyms. Deliberately never decode to text.
    if (0x20 <= keysym <= 0x7E or 0xA0 <= keysym <= 0xFF) or 0x01000100 <= keysym <= 0x0110FFFF:
        return EventClass.PRINTABLE
    return EventClass.OTHER
