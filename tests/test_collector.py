from countit.collector import MAX_ACTIVE_GAP_SECONDS, active_delta


def test_active_delta_excludes_idle_gaps():
    assert active_delta(None, 10) == 0
    assert active_delta(10, 11.5) == 1.5
    assert active_delta(10, 30) == MAX_ACTIVE_GAP_SECONDS
    assert active_delta(10, 9) == 0


def test_unsupported_sessions_do_not_connect(monkeypatch, tmp_path):
    import pytest

    from countit.collector import collect
    from countit.store import Store

    store = Store(tmp_path / "countit.db")
    try:
        monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
        with pytest.raises(RuntimeError, match="Wayland"):
            collect(store)
        monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
        monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
        monkeypatch.delenv("DISPLAY", raising=False)
        with pytest.raises(RuntimeError, match="DISPLAY is unset"):
            collect(store)
    finally:
        store.close()


def test_record_events_only_persist_aggregate_classes_and_cleanup(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from Xlib import X, display
    from Xlib.ext import record
    from Xlib.protocol import rq

    from countit.collector import collect
    from countit.model import EventClass
    from countit.store import Store

    monkeypatch.setenv("DISPLAY", ":synthetic")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    local = Mock()
    remote = Mock()
    local.keycode_to_keysym.return_value = ord("a")
    remote.record_create_context.return_value = 42
    displays = iter((local, remote))
    monkeypatch.setattr(display, "Display", lambda: next(displays))
    parser = Mock()
    parser.parse_binary_value.return_value = (SimpleNamespace(type=X.KeyPress, detail=38), b"")
    monkeypatch.setattr(rq, "EventField", lambda _: parser)

    def enable(context, callback):
        assert context == 42
        callback(
            SimpleNamespace(category=record.FromServer, client_swapped=False, data=b"synthetic")
        )
        raise KeyboardInterrupt

    remote.record_enable_context.side_effect = enable
    store = Store(tmp_path / "countit.db")
    try:
        store.add = Mock(wraps=store.add)
        collect(store)
        assert store.add.call_count == 1
        classification, timestamp, active = store.add.call_args.args
        assert classification is EventClass.PRINTABLE
        assert active == 0
        bucket = store.buckets_since(timestamp.replace(second=0, microsecond=0))[0]
        assert bucket.printable == 1
        local.record_disable_context.assert_called_once_with(42)
        remote.record_disable_context.assert_not_called()
        remote.record_free_context.assert_called_once_with(42)
        local.close.assert_called_once()
        remote.close.assert_called_once()
    finally:
        store.close()


def test_missing_record_extension_closes_displays(monkeypatch, tmp_path):
    from unittest.mock import Mock

    import pytest
    from Xlib import display

    from countit.collector import collect
    from countit.store import Store

    monkeypatch.setenv("DISPLAY", ":synthetic")
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    local = Mock()
    remote = Mock()
    remote.has_extension.return_value = False
    displays = iter((local, remote))
    monkeypatch.setattr(display, "Display", lambda: next(displays))
    store = Store(tmp_path / "countit.db")
    try:
        with pytest.raises(RuntimeError, match="RECORD"):
            collect(store)
        local.close.assert_called_once()
        remote.close.assert_called_once()
        with store.collector_lock():
            pass
    finally:
        store.close()
