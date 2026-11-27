# CountIt

> **Count the typing. Keep the typing private.** Your keyboard has said enough already.

CountIt is a small, local-only typing counter for Linux/X11. It keeps per-minute totals,
corrections, and rough WPM estimates. It does not keep what you typed. Some thoughts deserve
neither a database row nor a second reading.

This is **alpha software** for personal trends, not a measure of accuracy or productivity.
It has no cloud account, telemetry endpoint, leaderboard, or opinion about your career.

## What it does

- Collects aggregate key-event classes while you explicitly run `countit collect`.
- Stores per-minute SQLite buckets: printable keys, corrections, navigation keys, modifiers,
  other keys, and estimated active seconds.
- Shows gross WPM, a net-WPM estimate, and correction rate.
- Serves a dashboard on `127.0.0.1`, with no remote assets or external requests.
- Exports aggregates as CSV and deletes old buckets when asked.
- Includes an optional systemd user-service template. Installing CountIt enables nothing.

## Install

CountIt requires **Linux and Python 3.11 or later**. Collection additionally requires an
**X11 desktop session with the RECORD extension**. Wayland, including XWayland, is unsupported;
CountIt refuses collection there rather than presenting a partial count as the whole story.
Windows and macOS collection are not supported.

Once published on PyPI:

```bash
pipx install countit
countit --version
countit --help
```

For this checkout, before the first release:

```bash
git clone https://github.com/camilla007/countit.git
cd countit
pipx install .
```

Prefer a virtual environment? Use `python -m venv .venv`, then
`.venv/bin/python -m pip install .`. The command is `.venv/bin/countit`.
Never run the collector with `sudo`. Elevated privileges will not improve your spelling.

Upgrade a published installation with `pipx upgrade countit`.

## Use it

Start collection from a terminal in your X11 session:

```bash
countit collect
```

Press Ctrl-C to stop. Collection is session-wide: counts include activity in other applications
and password fields. X11 cannot reliably tell CountIt which fields are sensitive.
Only aggregate classes are stored; no character, keycode, key name, window title, process name,
clipboard content, or device identifier is saved. Raw key events exist briefly in memory to be
classified. This is data minimisation, not an invisibility cloak.

In another terminal:

```bash
countit serve
```

Open http://127.0.0.1:8765. The dashboard cannot start collection or delete data. It rejects
foreign hostnames and browser origins, sends no CORS permission, and tells browsers not to cache
responses. It has no authentication: other processes and users on the same machine may still
reach the local HTTP port. Run it only on a machine you trust, and stop it with Ctrl-C when done.

The default database is `$XDG_DATA_HOME/countit/countit.db`, or
`~/.local/share/countit/countit.db` if that variable is unset or not an absolute path. Use the same
`--database /path/to/countit.db` on each command to select another store. CountIt creates its
new data directory with mode `0700` and its database and SQLite sidecars with mode `0600`;
opening an existing store tightens those file permissions. It does not encrypt the database.

```bash
# The last day, or the last week if you enjoy a larger sample of yourself.
countit summary --hours 24
countit summary --hours 168

# CSV output contains aggregates. It still deserves a private file.
(umask 077; countit export --hours 24 > countit.csv)

# Delete buckets older than an explicit UTC cutoff. No undo, no ceremonial bin.
countit purge --before 2026-01-01T00:00:00Z
```

`--hours` accepts 1–8760. Purge requires a timezone and deletes whole minute buckets whose start
is before the cutoff. There is no automatic retention limit; purge deliberately. SQLite deletion
is not secure erasure, and copies, backups, exports, or journal remnants may retain old data.

## Metrics, with appropriate humility

| Metric | Meaning |
| --- | --- |
| **Gross WPM** | Printable key presses ÷ 5, normalised to estimated active time. |
| **Net WPM estimate** | `(printable − corrections) ÷ 5`, clamped at zero, normalised to active time. A useful estimate, not a performance review. |
| **Correction rate** | `(Backspace + Delete) ÷ printable`. The dashboard and summary show a percentage; CSV stores the ratio. It is not typing accuracy. |
| **Active seconds** | Each gap between recorded key presses contributes at most five seconds. A 30-second pause contributes five, not thirty or zero. The first event contributes none. |

All key classes contribute to active time, including navigation and modifiers. Time is credited
to the minute of the later event. Short samples can produce misleading WPM, and shortcut keys,
auto-repeat, keyboard layouts, composed characters, and input methods affect counts. CountIt
classifies base keysyms, not the text an application receives. One printable event is not
necessarily one character. Staring at the screen remains unquantified.

Only one collector may use a database at a time. Separate databases are independent; starting a
collector for each will count the same session in each. Use a local filesystem for the SQLite store.

## Optional user service

Start with `countit collect` and confirm it works. Then print the packaged template:

```bash
countit service-template
command -v countit
```

The template assumes pipx's default `~/.local/bin/countit` executable. Review and change
`ExecStart` if your installation differs. It contains no fixed display or personal home path.

```bash
mkdir -p ~/.config/systemd/user
countit service-template > ~/.config/systemd/user/countit-collector.service
# Review/edit the file before proceeding.
```

From your **X11 session**, import its environment; do not guess `DISPLAY` or the authority file:

```bash
systemctl --user import-environment DISPLAY XAUTHORITY XDG_SESSION_TYPE XDG_DATA_HOME
systemctl --user daemon-reload
systemctl --user enable --now countit-collector.service
systemctl --user status countit-collector.service --no-pager
```

This opts into background collection. The unit follows `graphical-session.target`, so automatic
start and stop depend on your desktop's systemd session integration. Refresh the imported
environment if your session changes. If it fails, inspect `journalctl --user -u
countit-collector.service`; do not run `xhost +` or weaken X11 access controls to make a counter happy.
The template disables core dumps for its process, since raw events briefly exist in memory.
For manual collection, use `ulimit -c 0` first if you also want to disable core dumps in that shell.

```bash
# Stop now, but keep the next-login opt-in.
systemctl --user stop countit-collector.service

# Stop now and remove that opt-in.
systemctl --user disable --now countit-collector.service
```

Stop and disable the service before uninstalling. `pipx uninstall countit` removes the package;
your aggregates remain until you delete them. A package manager is not your document shredder.

## Development and security

See [CONTRIBUTING.md](https://github.com/camilla007/countit/blob/main/CONTRIBUTING.md) for setup
and release steps, [SECURITY.md](https://github.com/camilla007/countit/blob/main/SECURITY.md)
for private vulnerability reporting and the privacy boundary, and
[CHANGELOG.md](https://github.com/camilla007/countit/blob/main/CHANGELOG.md) for changes.

Licensed under [MIT](https://github.com/camilla007/countit/blob/main/LICENSE), like Sandling.

---

Created by Camilla Buys. Type freely. Count modestly. Leave the words out of it.
