from datetime import UTC, datetime, timedelta
from pathlib import Path

from countit.model import EventClass
from countit.store import Store
from countit.web import to_csv, totals


def test_store_contains_only_aggregates(tmp_path: Path):
    store = Store(tmp_path / "countit.db")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    store.add(EventClass.PRINTABLE, now, 0)
    store.add(EventClass.CORRECTION, now + timedelta(seconds=1), 1)
    buckets = store.buckets_since(now - timedelta(minutes=1))
    assert len(buckets) == 1
    assert buckets[0].printable == 1 and buckets[0].corrections == 1
    assert totals(buckets)["correction_rate"] == 100.0
    assert "key" not in " ".join(
        row[1] for row in store.conn.execute("PRAGMA table_info(minute_buckets)")
    )
    assert "minute_utc" in to_csv(buckets)
    store.close()


def test_database_and_journal_permissions_are_private(tmp_path):
    import os
    import stat

    previous = os.umask(0)
    try:
        database = tmp_path / "private" / "countit.db"
        store = Store(database)
    finally:
        os.umask(previous)
    try:
        store.add(EventClass.PRINTABLE, datetime.now(UTC), 0)
        assert stat.S_IMODE(database.parent.stat().st_mode) == 0o700
        for path in database.parent.iterdir():
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
    finally:
        store.close()


def test_existing_database_permissions_are_tightened(tmp_path):
    database = tmp_path / "countit.db"
    database.touch(mode=0o644)
    store = Store(database)
    store.close()
    assert database.stat().st_mode & 0o777 == 0o600


def test_database_symlink_is_rejected(tmp_path):
    import pytest

    target = tmp_path / "unrelated"
    target.write_text("leave this alone")
    database = tmp_path / "countit.db"
    database.symlink_to(target)
    with pytest.raises(OSError):
        Store(database)
    assert target.read_text() == "leave this alone"


def test_collector_lock_blocks_duplicates_but_allows_readers(tmp_path):
    import pytest

    first = Store(tmp_path / "countit.db")
    second = Store(tmp_path / "countit.db")
    try:
        with first.collector_lock():
            with pytest.raises(RuntimeError, match="another collector"), second.collector_lock():
                pass
            assert second.buckets_since(datetime.now(UTC)) == []
        with second.collector_lock():
            pass
    finally:
        first.close()
        second.close()


def test_purge_respects_utc_cutoff_and_preserves_newer_buckets(tmp_path):
    store = Store(tmp_path / "countit.db")
    before = datetime(2026, 1, 1, tzinfo=UTC)
    try:
        store.add(EventClass.PRINTABLE, before - timedelta(minutes=1), 0)
        store.add(EventClass.PRINTABLE, before, 0)
        assert store.purge_before(before) == 1
        assert len(store.buckets_since(before)) == 1
        assert store.purge_before(before) == 0
    finally:
        store.close()
