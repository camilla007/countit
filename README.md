# CountIt

A local-only X11 typing telemetry proof of concept. It is intentionally **not** a text logger.

## Privacy contract

- No character, key name, keycode, window title, process name, clipboard content, or device identifier is persisted.
- The collector classifies each incoming X11 key press in memory, increments an aggregate counter, and discards the event.
- SQLite contains only minute buckets: printable key count, correction count, navigation count, modifier count, other count, and typing-active seconds.
- Collection is opt-in: `countit collect` must be running. The HTTP dashboard is read-only and binds only to `127.0.0.1`.
- This PoC cannot infer an X11 application's semantic field type, so do not mistake it for a password-field detector. Its privacy guarantee is that it retains no event contents or window identity at all.

`correction rate` is a proxy for editing behaviour, not accuracy. A real accuracy score requires an explicit typing test with reference text.

## Setup

This directory is already a virtual environment. Install the application and dependencies into it:

```bash
/home/camilla/enviros/countit_env/bin/pip install -e '.[dev]'
```

## Use

```bash
# Terminal 1: explicit opt-in collector
/home/camilla/enviros/countit_env/bin/countit collect --database ~/.local/share/countit/countit.db

# Terminal 2: local dashboard
/home/camilla/enviros/countit_env/bin/countit serve --database ~/.local/share/countit/countit.db
# Browse http://127.0.0.1:8765

countit summary --database ~/.local/share/countit/countit.db --hours 24
countit export --database ~/.local/share/countit/countit.db --hours 24 > countit.csv
countit purge --database ~/.local/share/countit/countit.db --before 2026-01-01T00:00:00+00:00
```

`collect` requires an X11 session and the X RECORD extension. It runs as the logged-in user; it does not open `/dev/input`, need root, install a keyboard driver, or inject input.

## Metrics

- **Gross WPM**: printable key presses / 5, per active typing minute.
- **Net WPM estimate**: `(printable - corrections) / 5`, clamped to zero, per active typing minute.
- **Correction rate**: `(Backspace + Delete) / printable`.
- **Typing-active seconds**: inter-key intervals up to 5 seconds; longer gaps are idle time.

All figures are estimates, useful for personal trends rather than assessment.

## User service

The supplied systemd user unit is deliberately disabled by default. Review its `ExecStart` and database path before copying it to `~/.config/systemd/user/` and enabling it.
