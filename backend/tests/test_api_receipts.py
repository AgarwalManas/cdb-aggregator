"""Tests for access receipts + permission simulation (item-29).

Receipts turn the audit log into a consumer-legible artifact; the simulator
turns granting from a blind checkbox into an informed preview. Both are derived
views, so the tests check the reshaping is faithful (accessor, purpose, cluster,
disclosed vs withheld, the "why" line) and that the simulation partitions the
field catalogue by the candidate scopes.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.receipts import build_receipt, simulate_permission
from app.consent import AuditEvent
from app.main import create_app
from app.models import ConsentScope


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


# --- Access receipts ---------------------------------------------------------


def test_receipts_cover_every_accessor_and_carry_structure(client: TestClient) -> None:
    receipts = client.get("/api/receipts").json()
    assert receipts
    # The seed exercises all three real accessors (aggregator, agent, counterparty).
    assert {r["accessorType"] for r in receipts} >= {"aggregator", "agent", "counterparty"}
    for r in receipts:
        assert r["receiptId"].startswith("rcpt-")
        assert r["purpose"] and r["clusterLabel"] and r["why"]
        assert "fields" in r and "withheld" in r


def test_receipts_show_allowed_and_denied_why_lines(client: TestClient) -> None:
    receipts = client.get("/api/receipts").json()
    allowed = [r for r in receipts if r["allowed"]]
    denied = [r for r in receipts if not r["allowed"]]
    assert allowed and denied
    assert "under an active grant" in allowed[0]["why"]
    assert "refused" in denied[0]["why"]


def test_receipt_builder_handles_unknown_actor_action_and_withheld() -> None:
    # Branches the seeded happy path can't reach: an unknown recipient/action and
    # a read that disclosed some clusters while withholding others.
    event = AuditEvent(
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        action="mystery_read",
        customer_id="cust-001",
        recipient="external:bureau",
        scope=ConsentScope.BALANCES,
        allowed=True,
        account_id="acc-1",
        consent_id="grant-x",
        record_count=1,
        withheld=("balances", "contact", "holdings"),
    )
    receipt = build_receipt(event, 0)
    assert receipt.accessor_type == "other"
    assert receipt.purpose == "mystery_read"  # falls back to the raw action
    assert receipt.withheld == ["Balances", "Contact", "Holdings"]
    assert "(grant-x)" in receipt.why


# --- Permission simulation ---------------------------------------------------


def test_simulation_partitions_fields_by_candidate_scopes(client: TestClient) -> None:
    sim = client.post(
        "/api/permission-simulation",
        json={"scopes": ["ACCOUNT_DETAILS", "BALANCES"]},
    ).json()
    visible_clusters = {f["cluster"] for f in sim["visible"]}
    withheld_clusters = {f["cluster"] for f in sim["withheld"]}
    assert visible_clusters == {"ACCOUNT_DETAILS", "BALANCES"}
    assert "TRANSACTIONS" in withheld_clusters
    assert not (visible_clusters & withheld_clusters)  # a field is on exactly one side
    # Every field carries an illustrative example.
    assert all(f["example"] for f in sim["visible"])


def test_simulation_with_no_scopes_withholds_everything() -> None:
    visible, withheld = simulate_permission([])
    assert visible == []
    assert withheld  # the whole catalogue is withheld when nothing is granted
