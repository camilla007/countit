from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .store import Store

PAGE = b'''<!doctype html><title>CountIt</title><style>body{font:16px system-ui;max-width:55rem;margin:2rem auto;color:#ddd;background:#161616}table{border-collapse:collapse}td,th{padding:.5rem;border-bottom:1px solid #555;text-align:right}th:first-child,td:first-child{text-align:left}.note{color:#bbb}</style><h1>CountIt</h1><p class=note>Aggregate-only local typing telemetry. Correction rate is not accuracy.</p><table><thead><tr><th>Period</th><th>Printable</th><th>Corrections</th><th>Gross WPM</th><th>Net WPM</th><th>Correction rate</th></tr></thead><tbody id=t></tbody></table><script>fetch('/api/summary?hours=24').then(r=>r.json()).then(d=>{const x=d.totals;document.querySelector('#t').innerHTML=`<tr><td>Last 24 hours</td><td>${x.printable}</td><td>${x.corrections}</td><td>${x.gross_wpm}</td><td>${x.net_wpm}</td><td>${x.correction_rate}%</td></tr>`})</script>'''


def totals(buckets: list) -> dict[str, int | float]:
    printable = sum(b.printable for b in buckets)
    corrections = sum(b.corrections for b in buckets)
    active = sum(b.active_seconds for b in buckets)
    denominator = active / 60
    return {"printable": printable, "corrections": corrections, "active_seconds": round(active, 1),
            "gross_wpm": round(printable / 5 / denominator, 1) if denominator else 0.0,
            "net_wpm": round(max(0, printable - corrections) / 5 / denominator, 1) if denominator else 0.0,
            "correction_rate": round(corrections / printable * 100, 1) if printable else 0.0}


def serve(database: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    class Handler(BaseHTTPRequestHandler):
        def buckets(self) -> list:
            try:
                hours = int(self.path.split("hours=")[-1]) if "hours=" in self.path else 24
            except ValueError:
                hours = 24
            hours = min(max(hours, 1), 24 * 365)
            store = Store(database)
            try:
                return store.buckets_since(datetime.now(UTC) - timedelta(hours=hours))
            finally:
                store.close()

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/":
                self.send_response(HTTPStatus.OK); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(PAGE); return
            if self.path.startswith("/api/summary"):
                body = json.dumps({"totals": totals(self.buckets())}).encode()
                self.send_response(HTTPStatus.OK); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body); return
            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()


def to_csv(buckets: list) -> str:
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["minute_utc", "printable", "corrections", "navigation", "modifiers", "other", "active_seconds", "gross_wpm", "net_wpm", "correction_rate"])
    for bucket in buckets:
        writer.writerow([bucket.minute_utc, bucket.printable, bucket.corrections, bucket.navigation, bucket.modifiers, bucket.other, f"{bucket.active_seconds:.1f}", f"{bucket.gross_wpm:.1f}", f"{bucket.net_wpm:.1f}", f"{bucket.correction_rate:.4f}"])
    return output.getvalue()
