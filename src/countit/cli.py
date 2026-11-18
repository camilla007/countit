from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .collector import collect
from .store import Store
from .web import serve, to_csv, totals

DEFAULT_DB = Path.home() / ".local/share/countit/countit.db"


def database_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--database", type=Path, default=DEFAULT_DB, help=f"SQLite aggregate store (default: {DEFAULT_DB})")


def main() -> None:
    parser = argparse.ArgumentParser(prog="countit", description="Local-only aggregate typing telemetry")
    sub = parser.add_subparsers(dest="command", required=True)
    collect_cmd = sub.add_parser("collect", help="start opt-in X11 aggregate collector"); database_arg(collect_cmd)
    serve_cmd = sub.add_parser("serve", help="serve a localhost dashboard"); database_arg(serve_cmd); serve_cmd.add_argument("--port", type=int, default=8765)
    summary_cmd = sub.add_parser("summary", help="print aggregate summary"); database_arg(summary_cmd); summary_cmd.add_argument("--hours", type=int, default=24)
    export_cmd = sub.add_parser("export", help="write aggregate buckets as CSV"); database_arg(export_cmd); export_cmd.add_argument("--hours", type=int, default=24)
    purge_cmd = sub.add_parser("purge", help="delete old aggregate buckets"); database_arg(purge_cmd); purge_cmd.add_argument("--before", required=True, help="ISO-8601 timestamp")
    args = parser.parse_args()
    if args.command == "collect":
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        store = Store(args.database)
        try:
            collect(store)
        finally:
            store.close()
    elif args.command == "serve":
        serve(args.database, port=args.port)
    else:
        store = Store(args.database)
        try:
            if args.command == "purge":
                before = datetime.fromisoformat(args.before).astimezone(UTC)
                print(f"deleted_buckets={store.purge_before(before)}")
            else:
                buckets = store.buckets_since(datetime.now(UTC) - timedelta(hours=args.hours))
                if args.command == "export":
                    print(to_csv(buckets), end="")
                else:
                    print(totals(buckets))
        finally:
            store.close()
