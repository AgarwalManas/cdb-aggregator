"""Tests for the health-check and root endpoints.

These are deliberately small — the point of Item 1 is a runnable, tested
skeleton, not coverage of business logic that doesn't exist yet. They prove the
app boots, the router is wired, and the response contract holds.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_health_ok() -> None:
    """/health returns 200 and a well-formed payload."""
    response = client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["service"]  # non-empty
    assert "version" in body


def test_root_points_at_docs() -> None:
    """The root endpoint advertises where to find docs and health."""
    response = client.get("/")
    assert response.status_code == 200

    body = response.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"
