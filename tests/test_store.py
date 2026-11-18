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
    assert "key" not in " ".join(row[1] for row in store.conn.execute("PRAGMA table_info(minute_buckets)"))
    assert "minute_utc" in to_csv(buckets)
    store.close()
