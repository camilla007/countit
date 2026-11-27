from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .store import Store

PAGE = (
    b"<!doctype html>"
    b"<title>CountIt</title>"
    b"<style>body{font:16px system-ui;max-width:55rem;margin:2rem auto;color:#ddd"
    b";background:#161616}table{border-collapse:collapse}td,th{padding:.5rem;bord"
    b"er-bottom:1px solid #555;text-align:right}th:first-child,td:first-child{tex"
    b"t-align:left}.note{color:#bbb}</style>"
    b"<h1>CountIt</h1>"
    b"<p class=note>Count the typing. Keep the typing private. Your keyboard has "
    b"said enough already.</p>"
    b"<p class=note>Correction rate is an editing proxy, not a performance review.</p>"
    b"<table>"
    b"<thead>"
    b"<tr>"
    b"<th>Period</th>"
    b"<th>Printable</th>"
    b"<th>Corrections</th>"
    b"<th>Gross WPM</th>"
    b"<th>Net WPM</th>"
    b"<th>Correction rate</th>"
    b"</tr>"
    b"</thead>"
    b"<tbody id=t>"
    b"</tbody>"
    b"</table>"
    b"<script>fetch('/api/summary?hours=24').then(r=>r.json()).then(d=>{const x=d"
    b".totals;document.querySelector('#t').innerHTML=`<tr>"
    b"<td>Last 24 hours</td>"
    b"<td>${x.printable}</td>"
    b"<td>${x.corrections}</td>"
    b"<td>${x.gross_wpm}</td>"
    b"<td>${x.net_wpm}</td>"
    b"<td>${x.correction_rate}%</td>"
    b"</tr>`})</script>"
)


def totals(buckets: list) -> dict[str, int | float]:
    printable = sum(b.printable for b in buckets)
    corrections = sum(b.corrections for b in buckets)
    active = sum(b.active_seconds for b in buckets)
    denominator = active / 60
    return {
        "printable": printable,
        "corrections": corrections,
        "active_seconds": round(active, 1),
        "gross_wpm": round(printable / 5 / denominator, 1) if denominator else 0.0,
        "net_wpm": round(max(0, printable - corrections) / 5 / denominator, 1)
        if denominator
        else 0.0,
        "correction_rate": round(corrections / printable * 100, 1) if printable else 0.0,
    }


def make_server(database: Path, port: int = 8765) -> ThreadingHTTPServer:
    """Bind only to IPv4 loopback; reject foreign browser origins and hostnames."""

    class Handler(BaseHTTPRequestHandler):
        def end_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            super().end_headers()

        def do_GET(self) -> None:  # noqa: N802
            port = self.server.server_address[1]
            hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if port == 80:
                hosts.update({"127.0.0.1", "localhost"})
            origins = {f"http://{host}" for host in hosts}
            if (
                self.headers.get("Host") not in hosts
                or self.headers.get("Origin") not in {None, *origins}
                or self.headers.get("Sec-Fetch-Site") not in {None, "none", "same-origin"}
            ):
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            try:
                request = urlsplit(self.path)
                if request.scheme or request.netloc:
                    raise ValueError
                if request.path == "/":
                    body = PAGE
                    content_type = "text/html; charset=utf-8"
                elif request.path == "/api/summary":
                    query = parse_qs(request.query, keep_blank_values=True)
                    values = query.get("hours", ["24"])
                    if set(query) - {"hours"} or len(values) != 1:
                        raise ValueError
                    hours = int(values[0])
                    if not 1 <= hours <= 24 * 365:
                        raise ValueError
                    store = Store(database)
                    try:
                        buckets = store.buckets_since(datetime.now(UTC) - timedelta(hours=hours))
                    finally:
                        store.close()
                    body = json.dumps({"totals": totals(buckets)}).encode()
                    content_type = "application/json"
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
            except ValueError:
                self.send_error(HTTPStatus.BAD_REQUEST, "hours must be an integer from 1 to 8760")
                return
            except (OSError, sqlite3.Error):
                self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "aggregate store unavailable")
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(database: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    if host != "127.0.0.1":
        raise ValueError("dashboard must bind to 127.0.0.1")
    with make_server(database, port) as server:
        print(f"CountIt dashboard: http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()


def to_csv(buckets: list) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "minute_utc",
            "printable",
            "corrections",
            "navigation",
            "modifiers",
            "other",
            "active_seconds",
            "gross_wpm",
            "net_wpm",
            "correction_rate",
        ]
    )
    for bucket in buckets:
        writer.writerow(
            [
                bucket.minute_utc,
                bucket.printable,
                bucket.corrections,
                bucket.navigation,
                bucket.modifiers,
                bucket.other,
                f"{bucket.active_seconds:.1f}",
                f"{bucket.gross_wpm:.1f}",
                f"{bucket.net_wpm:.1f}",
                f"{bucket.correction_rate:.4f}",
            ]
        )
    return output.getvalue()
