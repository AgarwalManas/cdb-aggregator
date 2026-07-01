"""Tests for the agent activity & authority console (item-28).

Item 11 gave the agent a scoped, revocable delegation. Item 28 makes that
authority visible and controllable in real time: a live action feed, an authority
card (pause / resume / revoke, time remaining), an approval queue for the
suggestion-only actions, and an intent → scope preview shown before granting.

The governance invariant is the whole point — pausing or revoking halts the feed
immediately (``live`` goes false) and refuses to run.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.agent import AGENT_ID, AGENT_NAME, REQUIRED_SCOPES
from app.api.demo import build_demo_state
from app.api.routes.agent import _authority_view, _halted_reason
from app.main import create_app
from app.models import Consent, ConsentScope, ConsentStatus

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _client() -> TestClient:
    return TestClient(create_app())


def _consent(
    status: ConsentStatus = ConsentStatus.GRANTED,
    *,
    created: datetime,
    expires: datetime,
    revoked: datetime | None = None,
) -> Consent:
    return Consent(
        consent_id="c-1",
        customer_id="cust-001",
        recipient=AGENT_ID,
        scopes=set(REQUIRED_SCOPES),
        status=status,
        created_at=created,
        expires_at=expires,
        revoked_at=revoked,
    )


# --- Authority card ----------------------------------------------------------


def test_authority_card_reports_scope_and_time_remaining() -> None:
    card = _client().get("/api/agent/authority").json()
    assert card["agentId"] == AGENT_ID
    assert card["agentName"] == AGENT_NAME
    assert card["status"] == "GRANTED"
    assert card["paused"] is False
    assert set(card["scopes"]) == {s.value for s in REQUIRED_SCOPES}
    assert card["accountIds"]  # capped at the balance-shared accounts
    assert card["secondsRemaining"] > 0


def test_authority_view_without_delegation_is_none_state() -> None:
    # No delegation → the card still renders, as "NONE" with no clock.
    view = _authority_view(build_demo_state(T0), None, T0)
    assert view.status == "NONE"
    assert view.paused is False
    assert view.scopes == []
    assert view.account_ids == []
    assert view.seconds_remaining is None


def test_authority_after_revoke_has_no_time_remaining() -> None:
    client = _client()
    client.post("/api/agent/delegation/revoke")
    card = client.get("/api/agent/authority").json()
    assert card["status"] == "REVOKED"
    assert card["secondsRemaining"] is None


# --- Pause / resume / revoke halt the feed -----------------------------------


def test_pause_halts_the_agent_then_resume_restores_it() -> None:
    client = _client()
    assert client.get("/api/agent/activity").json()["live"] is True

    paused = client.post("/api/agent/pause").json()
    assert paused["paused"] is True
    activity = client.get("/api/agent/activity").json()
    assert activity["live"] is False
    assert "paused" in activity["haltedReason"].lower()
    assert client.post("/api/agent/run").status_code == 409  # paused → refused

    resumed = client.post("/api/agent/resume").json()
    assert resumed["paused"] is False
    assert client.get("/api/agent/activity").json()["live"] is True
    assert client.post("/api/agent/run").status_code == 200


def test_revoke_halts_the_feed_and_redelegation_clears_pause() -> None:
    client = _client()
    assert client.get("/api/agent/activity").json()["live"] is True
    assert client.post("/api/agent/delegation/revoke").status_code == 200
    activity = client.get("/api/agent/activity").json()
    assert activity["live"] is False
    assert "revoked" in activity["haltedReason"].lower()

    # Pausing a revoked agent, then re-delegating, must come back live (not paused).
    client.post("/api/agent/pause")
    assert client.post("/api/agent/delegation").json()["status"] == "GRANTED"
    assert client.get("/api/agent/authority").json()["paused"] is False
    assert client.get("/api/agent/activity").json()["live"] is True


def test_halted_reason_covers_every_stopped_state() -> None:
    state = build_demo_state(T0)

    assert "no authority" in _halted_reason(state, None, T0).lower()

    active = _consent(created=T0, expires=T0 + timedelta(days=30))
    state.agent_paused = True
    assert "paused" in _halted_reason(state, active, T0).lower()
    state.agent_paused = False

    revoked = _consent(
        status=ConsentStatus.REVOKED,
        created=T0,
        expires=T0 + timedelta(days=30),
        revoked=T0 + timedelta(days=1),
    )
    assert "revoked" in _halted_reason(state, revoked, T0 + timedelta(days=2)).lower()

    expired = _consent(created=T0, expires=T0 + timedelta(days=1))
    assert "expired" in _halted_reason(state, expired, T0 + timedelta(days=2)).lower()

    # GRANTED but not yet active (future-dated) → the defensive fallback.
    future = _consent(created=T0 + timedelta(days=10), expires=T0 + timedelta(days=40))
    assert _halted_reason(state, future, T0) == "The agent has no active authority."


# --- Live action feed --------------------------------------------------------


def test_activity_feed_shows_only_the_agents_own_reads() -> None:
    feed = _client().get("/api/agent/activity").json()
    rows = feed["rows"]
    assert rows  # the seed ran the agent once
    for row in rows:
        assert row["status"] in {"authorized", "denied"}
        assert row["intent"]  # human phrase, not the raw action
        assert row["authorizingConsentId"]  # tied to the grant it relied on
    # Balance reads carry the source label resolved from the connection.
    assert any(r["action"] == "read_balances" and r["sourceLabel"] for r in rows)
    # Newest first.
    times = [r["occurredAt"] for r in rows]
    assert times == sorted(times, reverse=True)


# --- Approval queue ----------------------------------------------------------


def test_approval_queue_opens_with_a_pending_suggestion() -> None:
    approvals = _client().get("/api/agent/approvals").json()
    assert len(approvals) == 1
    assert approvals[0]["status"] == "PENDING"
    assert approvals[0]["suggestion"]["analyzed"]


def test_running_the_agent_queues_a_new_suggestion() -> None:
    client = _client()
    before = len(client.get("/api/agent/approvals").json())
    client.post("/api/agent/run")
    after = client.get("/api/agent/approvals").json()
    assert len(after) == before + 1
    assert after[0]["status"] == "PENDING"  # newest first


def test_approval_decisions_are_final() -> None:
    client = _client()
    apr_id = client.get("/api/agent/approvals").json()[0]["approvalId"]

    decided = client.post(
        f"/api/agent/approvals/{apr_id}/decision",
        json={"decision": "approve", "note": "looks right"},
    ).json()
    assert decided["status"] == "APPROVED"
    assert decided["note"] == "looks right"
    assert decided["decidedAt"]

    # A second decision on the same item is refused — decisions are final.
    again = client.post(f"/api/agent/approvals/{apr_id}/decision", json={"decision": "reject"})
    assert again.status_code == 409


def test_approval_decision_validates_id_and_verb() -> None:
    client = _client()
    apr_id = client.get("/api/agent/approvals").json()[0]["approvalId"]
    missing = client.post("/api/agent/approvals/nope/decision", json={"decision": "approve"})
    assert missing.status_code == 404  # unknown approval id
    bad_verb = client.post(f"/api/agent/approvals/{apr_id}/decision", json={"decision": "maybe"})
    assert bad_verb.status_code == 422  # unknown decision


def test_reject_and_request_changes_map_to_statuses() -> None:
    client = _client()
    client.post("/api/agent/run")
    client.post("/api/agent/run")
    ids = [a["approvalId"] for a in client.get("/api/agent/approvals").json()]
    rejected = client.post(
        f"/api/agent/approvals/{ids[0]}/decision", json={"decision": "reject"}
    ).json()
    assert rejected["status"] == "REJECTED"
    changes = client.post(
        f"/api/agent/approvals/{ids[1]}/decision", json={"decision": "request_changes"}
    ).json()
    assert changes["status"] == "CHANGES_REQUESTED"
    assert changes["note"] is None  # a note is optional


# --- Intent → scope preview --------------------------------------------------


def test_scope_preview_partitions_the_catalog() -> None:
    preview = _client().get("/api/agent/preview").json()
    assert preview["agentName"] == AGENT_NAME
    assert preview["durationDays"] == 30
    assert preview["accountCount"] == len(preview["accountIds"])
    visible = {s["scope"] for s in preview["visible"]}
    withheld = {s["scope"] for s in preview["withheld"]}
    assert visible == {s.value for s in REQUIRED_SCOPES}
    assert not (visible & withheld)  # a scope is either shown or withheld, never both
    assert ConsentScope.TRANSACTIONS.value in withheld  # the agent stays blind to these
