# Contributing

Small changes, useful tests, no accidental diary.

## Development

Use Linux and Python 3.11 or later. Tests use synthetic events and temporary databases; they do
not listen to your keyboard and need no X server. HTTP tests bind an ephemeral loopback port.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
.venv/bin/python -m ruff check src tests scripts
.venv/bin/python -m ruff format --check src tests scripts
.venv/bin/python -m build
.venv/bin/python -m twine check --strict dist/*
.venv/bin/python scripts/check_dist.py
```

Use a clean `dist/` directory for each build; move old artifacts aside first. The validator rejects
stale files. `python -m build` creates an sdist and builds the wheel from that sdist, so missing
source-package files cannot hide behind a working checkout.

Keep aggregate-only persistence, explicit collection, loopback-only serving, and no external
requests as invariants. Never add raw event logging, text reconstruction, application tracking,
auto-start on install, or silent uploading. Update tests for behavioural changes. Keep the
`systemd/` template and its packaged copy in `src/countit/data/` identical.

## Before the first PyPI release

1. Confirm that you can register `countit` on PyPI. A 404 is not a reservation: names may be
   prohibited or unavailable. If a different distribution name is needed, update metadata,
   installation docs, distribution checks, and publisher settings together.
2. Enable two-factor authentication on your PyPI account and retain recovery access.
3. Create a **pending Trusted Publisher** at https://pypi.org/manage/account/publishing/ with
   project `countit`, owner `camilla007`, repository `countit`, workflow **`release.yml`**, and
   environment **`pypi`**. If the project already exists under your account, configure its publisher
   in project settings instead.
4. In GitHub, create the **`pypi`** environment, require a human reviewer, and restrict deployment
   tags to reviewed release tags. If required reviewers are unavailable for your repository plan,
   treat pushing a release tag as the final publishing approval. Restrict tag creation and protect
   `main` as appropriate. No long-lived PyPI token is needed.
5. Review the MIT licence, package contents, privacy claims, and release notes. Run a manual
   collection/stop/restart check in a real X11 session, including the service if you intend to use
   it. The automated suite cannot certify your desktop's RECORD or systemd integration.

See PyPI's [Trusted Publishing guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
and [pending publisher setup](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
Setting up an account or publisher does not happen when you install this package. Mercifully.

## Release

1. Use a clean checkout of reviewed `main`; wait for all CI jobs to pass. CI tests Python
   3.11–3.14 and installs the built wheel into a separate environment for another test run.
2. Set the version in **`src/countit/__init__.py`** (the single version source), update the
   changelog, and merge the reviewed changes. Never reuse a published version.
3. Run the checks above and inspect both files in `dist/`. The sdist must contain the licence,
   docs, tests, and packaged service template; neither artifact should contain personal data.
4. Optionally rehearse on TestPyPI using a separate publisher and workflow/environment. Do not
   put TestPyPI into normal dependency resolution or use `--extra-index-url` as a shortcut.
5. When you intend to publish, create and push an annotated tag matching the version:

   ```bash
   git tag -a v0.1.0 -m 'CountIt 0.1.0'
   git push origin v0.1.0
   ```

   **Pushing this tag starts publishing**, subject to your configured environment approval.
   An ordinary push to `main` runs CI only. Do not push a tag merely to save your place.
6. The workflow reruns all checks, verifies tag/version agreement, and publishes the exact
   validated Python 3.13 build artifacts using OIDC. The publishing job has no source checkout;
   only that job receives `id-token: write`. Approve the `pypi` environment after review.
7. Check the PyPI page and install from PyPI in a fresh pipx/venv environment. Check `--version`,
   `--help`, and `service-template`. Confirm collection separately in an X11 session.

If a release is faulty, yank it on PyPI and publish a corrected version; do not overwrite files or
move an existing release tag. If upload partially succeeds, inspect PyPI before retrying. The
workflow deliberately does not skip existing files and pretend that a partial release is fine.
