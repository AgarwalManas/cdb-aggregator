"""Tests for the consent dashboard API (Item 9).

Exercises the endpoints the React client depends on: scopes, connections list,
grant, one-tap revoke, and the audit log — including that revocation flips a
connection's status and that the seeded audit trail contains a denied access.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_scopes_endpoint(client: TestClient) -> None:
    scopes = client.get("/api/scopes").json()
    keys = {s["scope"] for s in scopes}
    assert {"ACCOUNT_DETAILS", "BALANCES", "TRANSACTIONS"} <= keys
    assert all(s["label"] and s["description"] for s in scopes)


def test_connections_seeded(client: TestClient) -> None:
    connections = client.get("/api/connections").json()
    assert {c["sourceId"] for c in connections} == {"mock_fdx_bank", "legacy_bank", "scraper_bank"}
    fdx = next(c for c in connections if c["sourceId"] == "mock_fdx_bank")
    assert fdx["status"] == "GRANTED"
    assert "INVESTMENTS" not in fdx["scopes"]  # sanity: scopes are the enum values
    assert "INVESTMENT_HOLDINGS" in fdx["scopes"]
    assert fdx["expiresAt"] > fdx["createdAt"]


def test_grant_new_connection(client: TestClient) -> None:
    before = len(client.get("/api/connections").json())
    resp = client.post(
        "/api/connections",
        json={"sourceId": "legacy_bank", "scopes": ["ACCOUNT_DETAILS"], "durationDays": 30},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "GRANTED"
    assert body["scopes"] == ["ACCOUNT_DETAILS"]
    assert len(client.get("/api/connections").json()) == before + 1


def test_grant_rejects_unknown_source(client: TestClient) -> None:
    resp = client.post("/api/connections", json={"sourceId": "nope", "scopes": ["BALANCES"]})
    assert resp.status_code == 422


def test_one_tap_revoke(client: TestClient) -> None:
    connections = client.get("/api/connections").json()
    target = connections[0]["connectionId"]
    resp = client.post(f"/api/connections/{target}/revoke")
    assert resp.status_code == 200
    assert resp.json()["status"] == "REVOKED"
    assert resp.json()["revokedAt"] is not None
    # Reflected in the list.
    after = {c["connectionId"]: c for c in client.get("/api/connections").json()}
    assert after[target]["status"] == "REVOKED"


def test_revoke_unknown_connection_404(client: TestClient) -> None:
    assert client.post("/api/connections/does-not-exist/revoke").status_code == 404


def test_audit_log_has_allowed_and_denied(client: TestClient) -> None:
    events = client.get("/api/audit").json()
    assert len(events) >= 5
    assert any(e["allowed"] for e in events)
    denied = [e for e in events if not e["allowed"]]
    assert denied and denied[0]["reason"] == "ACCOUNT_NOT_COVERED"
    # Minimization is visible in the trail (record_count / withheld present).
    assert all("recordCount" in e and "withheld" in e for e in events)
