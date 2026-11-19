# CountIt

> **Count the typing. Keep the typing private.** Your keyboard has said enough already.

CountIt is a local-only X11 typing telemetry proof of concept: printable-key counts, corrections, active typing time, and a few WPM estimates. It deliberately refuses to become a text logger, a surveillance product, or an accidental diary of everything you typed while mildly sleep-deprived.

## What it does

- Collects aggregate X11 key-event classes while you explicitly run `countit collect`.
- Stores per-minute SQLite buckets: printable keys, corrections, navigation keys, modifiers, other keys, and typing-active seconds.
- Gives you gross WPM, net-WPM estimate, and correction rate.
- Serves a read-only dashboard on `127.0.0.1`. The internet has enough dashboards already.
- Exports aggregates as CSV and can purge old buckets.
- Includes a disabled-by-default systemd user-unit template for people who enjoy automation but still read `ExecStart` first.

## What it does **not** do

- Persist characters, key names, keycodes, window titles, process names, clipboard contents, or device identifiers.
- Open `/dev/input`, require root, install a keyboard driver, or inject input.
- Know whether an X11 field is a password field. X11 does not provide that semantic distinction reliably, so CountIt instead retains no field or event content whatsoever.
- Measure true typing accuracy. `correction rate` is an editing proxy: you may rewrite a sentence perfectly well, and you may leave a typo behind to prosper in the wild.

## Install

This checkout is already a virtual environment. Install the project into it:

```bash
cd /home/camilla/enviros/countit_env
bin/pip install -e '.[dev]'
```

Confirm that the command exists before entrusting it with your precious aggregates:

```bash
bin/countit --help
```

`collect` requires an X11 session and the X RECORD extension. It runs as your logged-in user.

## Use it

Start the explicit opt-in collector:

```bash
/home/camilla/enviros/countit_env/bin/countit collect \
  --database ~/.local/share/countit/countit.db
```

In another terminal, start the local dashboard:

```bash
/home/camilla/enviros/countit_env/bin/countit serve \
  --database ~/.local/share/countit/countit.db
```

Then open http://127.0.0.1:8765. It listens only on localhost, because neither your neighbours nor the broader internet needs an opinion on your Backspace habits.

Useful commands:

```bash
# The last day
countit summary --database ~/.local/share/countit/countit.db --hours 24

# The last week
countit summary --database ~/.local/share/countit/countit.db --hours 168

# CSV aggregates, should you wish to make a graph about it
countit export --database ~/.local/share/countit/countit.db --hours 24 > countit.csv

# Delete old aggregate buckets. This is irreversible. As intended.
countit purge --database ~/.local/share/countit/countit.db \
  --before 2026-01-01T00:00:00+00:00
```

## Metrics, with appropriate humility

| Metric | Meaning |
| --- | --- |
| **Gross WPM** | Printable key presses ÷ 5, normalised to active typing time. |
| **Net WPM estimate** | `(printable − corrections) ÷ 5`, clamped at zero, normalised to active typing time. A useful estimate, not a performance review. |
| **Correction rate** | `(Backspace + Delete) ÷ printable`. It measures correction behaviour, not truth, beauty, or orthographic virtue. |
| **Typing-active seconds** | Inter-key gaps of up to five seconds. Longer pauses are idle time; staring at the screen remains unquantified. |

All metrics are estimates intended for personal trends.

## Optional user service

CountIt does not quietly add itself to your login items. To run it automatically, review and install the supplied unit deliberately:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/countit-collector.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now countit-collector.service
```

Verify it:

```bash
systemctl --user status countit-collector.service --no-pager
```

Stop it without disabling future automatic starts:

```bash
systemctl --user stop countit-collector.service
```

Disable it and stop it:

```bash
systemctl --user disable --now countit-collector.service
```

---

**Type freely. Aggregate ruthlessly. Store nothing embarrassing.**
