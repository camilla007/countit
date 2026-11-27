from __future__ import annotations

import os
import sqlite3
import stat
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .model import Bucket, EventClass

SCHEMA = """
CREATE TABLE IF NOT EXISTS minute_buckets (
    minute_utc TEXT PRIMARY KEY,
    printable INTEGER NOT NULL DEFAULT 0 CHECK (printable >= 0),
    corrections INTEGER NOT NULL DEFAULT 0 CHECK (corrections >= 0),
    navigation INTEGER NOT NULL DEFAULT 0 CHECK (navigation >= 0),
    modifiers INTEGER NOT NULL DEFAULT 0 CHECK (modifiers >= 0),
    other INTEGER NOT NULL DEFAULT 0 CHECK (other >= 0),
    active_seconds REAL NOT NULL DEFAULT 0 CHECK (active_seconds >= 0)
);
"""


class Store:
    def __init__(self, database: Path) -> None:
        self.database = database
        database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Create privately before SQLite opens the file; WAL files inherit this mode.
        fd = os.open(database, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise OSError("database must be a regular file")
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        for suffix in ("-wal", "-shm", "-journal"):
            try:
                fd = os.open(str(database) + suffix, os.O_RDONLY | os.O_NOFOLLOW)
            except FileNotFoundError:
                continue
            try:
                os.fchmod(fd, 0o600)
            finally:
                os.close(fd)
        self.conn = sqlite3.connect(database)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute(SCHEMA)
        self.conn.commit()

    @contextmanager
    def collector_lock(self):
        """Only one collector may add events to this database at a time."""
        import fcntl

        with self.database.open("rb") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("another collector is already using this database") from exc
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    @staticmethod
    def minute(timestamp: datetime) -> str:
        return timestamp.astimezone(UTC).replace(second=0, microsecond=0).isoformat()

    def add(self, event: EventClass, timestamp: datetime, active_seconds: float) -> None:
        column = {
            EventClass.PRINTABLE: "printable",
            EventClass.CORRECTION: "corrections",
            EventClass.NAVIGATION: "navigation",
            EventClass.MODIFIER: "modifiers",
            EventClass.OTHER: "other",
        }[event]
        minute = self.minute(timestamp)
        self.conn.execute(
            f"INSERT INTO minute_buckets(minute_utc, {column}, active_seconds) VALUES (?, 1, ?) "
            f"ON CONFLICT(minute_utc) DO UPDATE SET {column}={column}+1, "
            "active_seconds=active_seconds+excluded.active_seconds",
            (minute, active_seconds),
        )
        self.conn.commit()

    def buckets_since(self, since: datetime) -> list[Bucket]:
        rows = self.conn.execute(
            "SELECT minute_utc, printable, corrections, navigation, modifiers, "
            "other, active_seconds "
            "FROM minute_buckets WHERE minute_utc >= ? ORDER BY minute_utc",
            (since.astimezone(UTC).isoformat(),),
        ).fetchall()
        return [Bucket(*row) for row in rows]

    def purge_before(self, before: datetime) -> int:
        cursor = self.conn.execute(
            "DELETE FROM minute_buckets WHERE minute_utc < ?", (before.astimezone(UTC).isoformat(),)
        )
        self.conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        self.conn.close()
