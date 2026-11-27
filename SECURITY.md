# Security policy

Report suspected vulnerabilities privately to **camilla.buys@gmail.com**, the same contact used
by Sandling. Include the version, impact, and minimal reproduction steps with synthetic data.
Do not attach real typing records, credentials, Xauthority files, or a core dump.

Security fixes target the latest published release and `main`. CountIt is currently alpha.

## Privacy boundary

CountIt processes raw X11 events in memory, classifies them, and persists aggregate minute
buckets only. It does not send data to an external service, record text, distinguish password
fields, or promise protection from a compromised operating system or another process running
as your user. Activity totals can still reveal routines. Treat them as personal data.

Collection is explicit, session-wide, and Linux/X11 only. Package installation does not start a
collector or install a service. The optional systemd unit requires deliberate setup and disables
core dumps. For manual collection, core-dump policy is inherited from your shell and OS.

SQLite files are owner-readable/writable; new data directories are owner-only. Existing parent
directory permissions are left alone. Use a private directory on a local filesystem. Data is
not encrypted. Export permissions and backup retention are your responsibility. Purge removes
rows logically, not through secure erasure.

The HTTP dashboard binds only to `127.0.0.1`, checks Host/Origin/Fetch Metadata, has no CORS
allowance, and sends `Cache-Control: no-store`. It serves no remote assets. It has no login and
is not intended for shared or hostile machines: local users and processes can reach its port.
Do not proxy it to a network-facing address. Its HTTP interface has no collection or deletion
endpoints.

## Release boundary

The release workflow uses PyPI Trusted Publishing with OIDC and a dedicated GitHub environment.
Builds and tests run without publishing credentials. The publishing job receives only the built
artifacts and has no source checkout. Configure required reviewers on the `pypi` environment
before using the workflow. Never commit API tokens, `.pypirc`, live databases, or exports.
