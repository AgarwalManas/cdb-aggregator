"""Tests for the portable alias + consent-gated resolver (item-31).

The pattern is "route on a lookup, not on the identifier": resolving the user's
bank-neutral handle returns a one-time routing token — never the raw
institution / transit / account — and only when an active, in-scope consent
covers the target. Re-pointing is a scoped, logged event, and every resolution
(allowed or denied) lands in the traceability trail.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.alias import AliasRegistry, coordinates_for
from app.api.demo import ALIAS_HANDLE, build_demo_state
from app.main import create_app

T0 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


# --- The portable-address card -----------------------------------------------


def test_alias_card_shows_masked_target_and_history(client: TestClient) -> None:
    card = client.get("/api/alias").json()
    assert card["handle"] == ALIAS_HANDLE
    # The card shows the bank + a masked account, never raw coordinates.
    assert card["target"]["sourceLabel"] == "Legacy Bank"
    assert "····" in card["target"]["display"]
    assert card["options"]  # the connected accounts it could point at
    assert len(card["history"]) == 1  # the seeded resolution
    assert card["history"][0]["allowed"] is True
    assert card["history"][0]["disclosed"] == "one-time routing token"


def test_options_drop_a_revoked_connection(client: TestClient) -> None:
    before = {o["accountId"] for o in client.get("/api/alias").json()["options"]}
    assert "leg-sav" in before
    # Revoke the Legacy Bank connection → its account can no longer be a target.
    connections = client.get("/api/connections").json()
    leg = next(c for c in connections if c["accountIds"] == ["leg-sav"])
    client.post(f"/api/connections/{leg['connectionId']}/revoke")
    after = {o["accountId"] for o in client.get("/api/alias").json()["options"]}
    assert "leg-sav" not in after


# --- Resolution: consent-gated, tokenized, logged ----------------------------


def test_resolve_returns_a_one_time_token_never_coordinates(client: TestClient) -> None:
    res = client.post("/api/alias/resolve", json={"requester": "counterparty:acme"}).json()
    assert res["allowed"] is True
    assert res["routingToken"]  # opaque token, not coordinates
    assert res["disclosed"] == "one-time routing token"
    # The counterparty payload carries no institution / transit / account.
    assert "institution" not in res and "transit" not in res

    # It shows up in the trail, attributed to whoever asked.
    history = client.get("/api/alias").json()["history"]
    assert history[0]["requester"] == "counterparty:acme"


def test_resolve_is_refused_without_an_active_grant(client: TestClient) -> None:
    connections = client.get("/api/connections").json()
    leg = next(c for c in connections if c["accountIds"] == ["leg-sav"])
    client.post(f"/api/connections/{leg['connectionId']}/revoke")  # revoke the target's grant

    res = client.post("/api/alias/resolve", json={}).json()
    assert res["allowed"] is False
    assert res["routingToken"] is None
    assert res["disclosed"] == "nothing"
    assert res["reason"]  # the denial reason is surfaced
    # The denied resolution is still recorded.
    assert client.get("/api/alias").json()["history"][0]["allowed"] is False


def test_token_redeems_once_then_is_spent(client: TestClient) -> None:
    token = client.post("/api/alias/resolve", json={}).json()["routingToken"]
    ok = client.post("/api/alias/exchange", json={"token": token})
    assert ok.status_code == 200
    coords = ok.json()
    assert coords["sourceLabel"] == "Legacy Bank"
    assert coords["institution"] and coords["transit"]
    # A second redemption of the same token is refused — single-use.
    assert client.post("/api/alias/exchange", json={"token": token}).status_code == 410


def test_exchange_unknown_token_is_gone(client: TestClient) -> None:
    assert client.post("/api/alias/exchange", json={"token": "nope"}).status_code == 410


# --- Re-pointing: a scoped, logged portability event -------------------------


def test_repoint_to_a_connected_account_moves_the_target(client: TestClient) -> None:
    updated = client.post("/api/alias/repoint", json={"accountId": "fdx-chq"}).json()
    assert updated["target"]["accountId"] == "fdx-chq"
    assert updated["target"]["sourceLabel"] == "Mock FDX Bank"
    assert updated["repointedAt"] is not None


def test_repoint_to_an_unconnected_account_is_refused(client: TestClient) -> None:
    # No such connection → not a valid routing target.
    assert client.post("/api/alias/repoint", json={"accountId": "ghost"}).status_code == 400


# --- Resolver unit branches the API can't reach ------------------------------


def test_resolver_rejects_unknown_alias_and_handle() -> None:
    state = build_demo_state(T0)
    unknown = state.resolver.resolve("nobody.cdb", requester="x", at=T0)
    assert unknown.allowed is False
    assert unknown.reason == "unknown alias"
    # Re-pointing an unknown handle is a no-op (returns None).
    assert state.resolver.repoint("nobody.cdb", "leg-sav", at=T0) is None


def test_token_expires_after_its_ttl() -> None:
    state = build_demo_state(T0)
    res = state.resolver.resolve(ALIAS_HANDLE, requester="x", at=T0)
    # Redeeming an hour later (well past the TTL) yields nothing.
    assert state.resolver.exchange(res.routing_token, at=T0 + timedelta(hours=1)) is None


def test_registry_register_repoint_and_list() -> None:
    registry = AliasRegistry()
    assert registry.get("a.cdb") is None
    registry.register("a.cdb", "acc-1", at=T0)
    registry.repoint("a.cdb", "acc-2", at=T0 + timedelta(minutes=1))
    alias = registry.get("a.cdb")
    assert alias.account_id == "acc-2"
    assert alias.repointed_at == T0 + timedelta(minutes=1)
    assert [a.handle for a in registry.all()] == ["a.cdb"]


def test_coordinates_are_deterministic_and_masked() -> None:
    a = coordinates_for("leg-sav", "Legacy Bank")
    b = coordinates_for("leg-sav", "Legacy Bank")
    assert a == b  # stable, no randomness
    assert a.masked_account.startswith("····")
    assert a.institution == "002"
