from __future__ import annotations

import logging
import os
import signal
import threading
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from time import monotonic

from .classify import classify_keysym
from .store import Store

LOG = logging.getLogger(__name__)
MAX_ACTIVE_GAP_SECONDS = 5.0


def active_delta(previous: float | None, current: float) -> float:
    """Credit each inter-key interval with at most five seconds of activity."""
    if previous is None:
        return 0.0
    return min(max(current - previous, 0.0), MAX_ACTIVE_GAP_SECONDS)


@contextmanager
def stop_on_sigterm():
    """Let systemd stops use the same cleanup path as Ctrl-C."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return

    def stop(signum, frame):
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, stop)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def collect(store: Store) -> None:
    """Run an X11 RECORD listener. Key events are classified then discarded."""
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or os.environ.get(
        "WAYLAND_DISPLAY"
    ):
        raise RuntimeError("collection requires an X11 session; Wayland/XWayland is unsupported")
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("DISPLAY is unset; run collection from your logged-in X11 session")
    try:
        from Xlib import X, display, error
        from Xlib.ext import record
        from Xlib.protocol import rq
    except ImportError as exc:
        raise RuntimeError("python-xlib is required; reinstall countit") from exc

    with store.collector_lock(), stop_on_sigterm(), ExitStack() as stack:
        try:
            local = display.Display()
            stack.callback(local.close)
            record_display = display.Display()
            stack.callback(record_display.close)
        except error.DisplayError as exc:
            raise RuntimeError("cannot open X11 display; check DISPLAY and XAUTHORITY") from exc
        if not record_display.has_extension("RECORD"):
            raise RuntimeError("X server does not expose the RECORD extension")
        context = record_display.record_create_context(
            0,
            [record.AllClients],
            [
                {
                    "core_requests": (0, 0),
                    "core_replies": (0, 0),
                    "ext_requests": (0, 0, 0, 0),
                    "ext_replies": (0, 0, 0, 0),
                    "delivered_events": (0, 0),
                    "device_events": (X.KeyPress, X.KeyPress),
                    "errors": (0, 0),
                    "client_started": False,
                    "client_died": False,
                }
            ],
        )
        previous: float | None = None

        def handle(reply: object) -> None:
            nonlocal previous
            if getattr(reply, "category", None) != record.FromServer or getattr(
                reply, "client_swapped", False
            ):
                return
            data = getattr(reply, "data", b"")
            while data:
                event, data = rq.EventField("").parse_binary_value(
                    data, record_display.display, None, None
                )
                if event.type != X.KeyPress:
                    continue
                classification = classify_keysym(local.keycode_to_keysym(event.detail, 0))
                now = monotonic()
                store.add(classification, datetime.now(UTC), active_delta(previous, now))
                previous = now

        LOG.info("collector started; raw key event contents are never persisted")
        try:
            record_display.record_enable_context(context, handle)
        except KeyboardInterrupt:
            LOG.info("collector stopped")
        finally:
            # RECORD's enabled connection is busy: disable it via the other connection.
            local.record_disable_context(context)
            local.sync()
            record_display.record_free_context(context)
            record_display.flush()
