"""Tests for serving the built React app from the API.

The deploy image runs one process that hosts both the JSON API and the compiled
single-page app (see the Dockerfile / render.yaml). These tests cover that
opt-in path — enabled by `CDB_FRONTEND_DIST` — without needing a real build:
we point the setting at a throwaway directory holding a stand-in index.html.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import _frontend_dist, create_app


def _client(monkeypatch: pytest.MonkeyPatch, frontend_dist: str) -> TestClient:
    """Build a TestClient for an app with CDB_FRONTEND_DIST overridden."""
    monkeypatch.setenv("CDB_FRONTEND_DIST", frontend_dist)
    get_settings.cache_clear()
    client = TestClient(create_app())
    get_settings.cache_clear()  # don't leak the override into other tests
    return client


def test_serves_index_html_at_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With CDB_FRONTEND_DIST set, "/" returns the built index.html, not JSON."""
    (tmp_path / "index.html").write_text("<!doctype html><title>CDB</title>", "utf-8")

    response = _client(monkeypatch, str(tmp_path)).get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>CDB</title>" in response.text


def test_api_still_wins_over_static_mount(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mounting the SPA at "/" must not shadow the API or health routes."""
    (tmp_path / "index.html").write_text("<!doctype html>spa", "utf-8")

    client = _client(monkeypatch, str(tmp_path))

    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/net-worth").status_code == 200


def test_missing_dir_falls_back_to_json_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configured-but-absent dist directory falls back to the JSON root."""
    client = _client(monkeypatch, str(tmp_path / "does-not-exist"))
    body = client.get("/").json()

    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_frontend_dist_helper_handles_none_and_missing(tmp_path: Path) -> None:
    """The resolver returns None for unset or non-directory paths, a Path for real ones."""
    assert _frontend_dist(None) is None
    assert _frontend_dist("") is None
    assert _frontend_dist(str(tmp_path / "nope")) is None
    assert _frontend_dist(str(tmp_path)) == tmp_path
