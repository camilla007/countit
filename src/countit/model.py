from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EventClass(StrEnum):
    PRINTABLE = "printable"
    CORRECTION = "correction"
    NAVIGATION = "navigation"
    MODIFIER = "modifier"
    OTHER = "other"


@dataclass(frozen=True)
class Bucket:
    minute_utc: str
    printable: int
    corrections: int
    navigation: int
    modifiers: int
    other: int
    active_seconds: float

    @property
    def gross_wpm(self) -> float:
        return self.printable / 5 / (self.active_seconds / 60) if self.active_seconds else 0.0

    @property
    def net_wpm(self) -> float:
        net = max(0, self.printable - self.corrections)
        return net / 5 / (self.active_seconds / 60) if self.active_seconds else 0.0

    @property
    def correction_rate(self) -> float:
        return self.corrections / self.printable if self.printable else 0.0
