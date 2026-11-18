from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import monotonic

from .classify import classify_keysym
from .store import Store

LOG = logging.getLogger(__name__)
MAX_ACTIVE_GAP_SECONDS = 5.0


def active_delta(previous: float | None, current: float) -> float:
    """Count only short intervals; long pauses are idle, not typing time."""
    if previous is None:
        return 0.0
    return min(max(current - previous, 0.0), MAX_ACTIVE_GAP_SECONDS)


def collect(store: Store) -> None:
    """Run an X11 RECORD listener. Key events are classified then discarded."""
    try:
        from Xlib import X, display
        from Xlib.ext import record
        from Xlib.protocol import rq
    except ImportError as exc:
        raise RuntimeError("python-xlib is required; install this project first") from exc

    local = display.Display()
    record_display = display.Display()
    if not record_display.has_extension("RECORD"):
        raise RuntimeError("X server does not expose the RECORD extension")
    context = record_display.record_create_context(
        0, [record.AllClients],
        [{"core_requests": (0, 0), "core_replies": (0, 0), "ext_requests": (0, 0, 0, 0),
          "ext_replies": (0, 0, 0, 0), "delivered_events": (0, 0),
          "device_events": (X.KeyPress, X.KeyPress), "errors": (0, 0),
          "client_started": False, "client_died": False}],
    )
    previous: float | None = None

    def handle(reply: object) -> None:
        nonlocal previous
        if getattr(reply, "category", None) != record.FromServer or getattr(reply, "client_swapped", False):
            return
        data = getattr(reply, "data", b"")
        while data:
            event, data = rq.EventField("").parse_binary_value(data, record_display.display, None, None)
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
        try:
            record_display.record_disable_context(context)
            record_display.flush()
            record_display.record_free_context(context)
        finally:
            local.close()
            record_display.close()
