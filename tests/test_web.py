import http.client
import threading

import pytest

from countit.web import make_server, serve


@pytest.fixture
def dashboard(tmp_path):
    database = tmp_path / "countit.db"
    server = make_server(database, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, database
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(server, path="/", headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        conn.request("GET", path, headers=headers or {})
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


def test_loopback_dashboard_and_summary(dashboard):
    server, database = dashboard
    assert server.server_address[0] == "127.0.0.1"
    status, headers, body = request(server)
    assert status == 200
    assert b"Your keyboard has said enough" in body
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Frame-Options"] == "DENY"
    status, _, body = request(server, "/api/summary?hours=24")
    assert status == 200
    assert b'"printable": 0' in body
    assert database.exists()


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "attacker.example"},
        {"Origin": "https://attacker.example"},
        {"Origin": "null"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_foreign_browser_requests_cannot_read_or_create_store(dashboard, headers):
    server, database = dashboard
    assert request(server, "/api/summary", headers)[0] == 403
    assert not database.exists()


@pytest.mark.parametrize("query", ["hours=0", "hours=8761", "hours=x", "hours=", "hours=1&hours=2"])
def test_invalid_hours(dashboard, query):
    server, database = dashboard
    assert request(server, "/api/summary?" + query)[0] == 400
    assert not database.exists()


def test_routes_are_exact(dashboard):
    assert request(dashboard[0], "/api/summary-extra")[0] == 404


def test_non_loopback_binding_is_refused(tmp_path):
    with pytest.raises(ValueError, match="127.0.0.1"):
        serve(tmp_path / "countit.db", host="0.0.0.0")
