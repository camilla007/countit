from __future__ import annotations

import argparse
import logging
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from pathlib import Path

from . import __version__
from .collector import collect
from .store import Store
from .web import serve, to_csv, totals


def default_database() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share").expanduser()
    if not base.is_absolute():
        base = Path.home() / ".local/share"
    return base / "countit/countit.db"


def database_arg(parser: argparse.ArgumentParser) -> None:
    default = default_database()
    parser.add_argument(
        "--database",
        type=lambda value: Path(value).expanduser(),
        default=default,
        help=f"SQLite aggregate store (default: {default})",
    )


def hours_arg(value: str) -> int:
    try:
        hours = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("hours must be a whole number") from exc
    if not 1 <= hours <= 24 * 365:
        raise argparse.ArgumentTypeError("hours must be between 1 and 8760")
    return hours


def timestamp_arg(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use an ISO-8601 timestamp with a timezone") from exc
    if timestamp.tzinfo is None:
        raise argparse.ArgumentTypeError("include a timezone, for example 2026-01-01T00:00:00Z")
    return timestamp.astimezone(UTC)


def port_arg(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be a whole number") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="countit",
        description="Count the typing. Keep the typing private.",
        epilog="No words. No leaderboard. Your Backspace habits remain your own.",
    )
    parser.add_argument("--version", action="version", version=f"CountIt {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    collect_cmd = sub.add_parser("collect", help="start the opt-in X11 aggregate collector")
    database_arg(collect_cmd)
    serve_cmd = sub.add_parser("serve", help="serve a dashboard on 127.0.0.1")
    database_arg(serve_cmd)
    serve_cmd.add_argument("--port", type=port_arg, default=8765)
    for command, help_text in (
        ("summary", "print aggregate summary"),
        ("export", "write aggregate buckets as CSV"),
    ):
        command_parser = sub.add_parser(command, help=help_text)
        database_arg(command_parser)
        command_parser.add_argument("--hours", type=hours_arg, default=24)
    purge_cmd = sub.add_parser("purge", help="permanently delete old aggregate buckets")
    database_arg(purge_cmd)
    purge_cmd.add_argument(
        "--before", required=True, type=timestamp_arg, help="ISO-8601 timestamp with timezone"
    )
    sub.add_parser("service-template", help="print an optional systemd unit; install nothing")
    args = parser.parse_args(argv)
    try:
        if args.command == "service-template":
            print(files("countit").joinpath("data/countit-collector.service").read_text(), end="")
        elif args.command == "serve":
            serve(args.database, port=args.port)
        else:
            store = Store(args.database)
            try:
                if args.command == "collect":
                    logging.basicConfig(
                        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
                    )
                    collect(store)
                elif args.command == "purge":
                    print(f"deleted_buckets={store.purge_before(args.before)}")
                else:
                    buckets = store.buckets_since(datetime.now(UTC) - timedelta(hours=args.hours))
                    if args.command == "export":
                        print(to_csv(buckets), end="")
                    else:
                        print(totals(buckets))
            finally:
                store.close()
    except KeyboardInterrupt:
        return
    except (OSError, RuntimeError, sqlite3.Error) as exc:
        parser.exit(1, f"countit: {exc}\n")
