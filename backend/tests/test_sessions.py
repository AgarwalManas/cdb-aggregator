"""Per-visitor session isolation and the demo-reset endpoint.

The demo world is mutable, so each browser session gets its own copy: one
visitor's revoke must never be visible to another, and a reset restores only the
caller's world. These tests pin that behavior end-to-end (through the session
middleware) and unit-test the LRU-bounded store directly.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.session import SESSION_COOKIE, SessionStore, new_session_id
from app.main import create_app


def _statuses(client: TestClient) -> dict[str, str]:
    """Map connectionId -> status for a client's own session world."""
    return {c["connectionId"]: c["status"] for c in client.get("/api/connections").json()}


# --- SessionStore unit -------------------------------------------------------


def test_store_creates_once_and_reuses() -> None:
    store = SessionStore()
    first = store.get_or_create("s1")
    again = store.get_or_create("s1")  # existing -> move_to_end, same object back
    assert again is first
    assert len(store) == 1


def test_store_reset_replaces_world() -> None:
    store = SessionStore()
    original = store.get_or_create("s1")
    fresh = store.reset("s1")
    assert fresh is not original
    assert store.get_or_create("s1") is fresh
    assert len(store) == 1


def test_store_evicts_when_over_capacity() -> None:
    store = SessionStore(max_sessions=2)
    store.get_or_create("a")
    store.get_or_create("b")
    store.get_or_create("a")  # touch 'a' so 'b' becomes least-recently used
    store.get_or_create("c")  # over cap -> evict the LRU entry
    assert len(store) == 2


def test_new_session_id_is_unique_and_opaque() -> None:
    ids = {new_session_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(len(i) >= 16 for i in ids)


# --- Middleware + dependency (integration) -----------------------------------


def test_first_request_mints_a_session_cookie() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/net-worth")
    assert resp.status_code == 200
    assert resp.cookies.get(SESSION_COOKIE) is not None


def test_subsequent_request_reuses_the_cookie() -> None:
    client = TestClient(create_app())
    client.get("/api/net-worth")  # mints the cookie, stored in the client jar
    resp = client.get("/api/net-worth")  # already has it -> no new Set-Cookie
    assert "set-cookie" not in resp.headers


def test_two_visitors_have_isolated_worlds() -> None:
    app = create_app()
    a, b = TestClient(app), TestClient(app)

    target = next(cid for cid, st in _statuses(a).items() if st == "GRANTED")
    assert a.post(f"/api/connections/{target}/revoke").status_code == 200

    assert _statuses(a)[target] == "REVOKED"  # A's change stuck for A
    assert _statuses(b)[target] == "GRANTED"  # ...and left B untouched


def test_reset_restores_only_the_callers_world() -> None:
    client = TestClient(create_app())
    target = next(cid for cid, st in _statuses(client).items() if st == "GRANTED")
    client.post(f"/api/connections/{target}/revoke")
    assert _statuses(client)[target] == "REVOKED"

    assert client.post("/api/demo/reset").status_code == 204
    assert _statuses(client)[target] == "GRANTED"  # back to the seeded state
