"""Tests for the user-verifiable audit chain endpoint (item-30).

The point of item-30 is that a browser can recompute the hash chain itself and
not trust the server's "valid: true". These tests stand in for that browser:
they rebuild each entry's SHA-256 preimage from *only* the published fields —
an independent reimplementation of the client verifier — and confirm it
reproduces every ``entry_hash`` and the published head. If the endpoint ever
stopped exposing a field the hash depends on, or changed a serialization, this
would catch it. Tampering with any field must break the recomputation.
"""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _preimage(entry: dict, prev_hash: str) -> str:
    """Rebuild the hashed string from published fields — mirrors the JS verifier."""
    return "|".join(
        (
            prev_hash,
            entry["occurredAt"],
            entry["action"],
            entry["customerId"],
            entry["recipient"],
            entry["scope"],
            "1" if entry["allowed"] else "0",
            entry["accountId"] or "",
            entry["reason"] or "",
            entry["consentId"] or "",
            str(entry["recordCount"]),
            ",".join(entry["withheld"]),
        )
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_chain_publishes_head_and_algorithm(client: TestClient) -> None:
    chain = client.get("/api/audit/chain").json()
    assert chain["algorithm"] == "SHA-256"
    assert chain["genesis"] == "0" * 64
    assert chain["entries"]
    assert chain["head"] == chain["entries"][-1]["entryHash"]


def test_chain_recomputes_independently_from_published_fields(client: TestClient) -> None:
    chain = client.get("/api/audit/chain").json()
    prev = chain["genesis"]
    for entry in chain["entries"]:
        assert entry["prevHash"] == prev  # the links join up
        assert _sha256(_preimage(entry, prev)) == entry["entryHash"]  # and each hash checks out
        prev = entry["entryHash"]
    assert prev == chain["head"]


def test_altering_any_field_breaks_the_recomputation(client: TestClient) -> None:
    chain = client.get("/api/audit/chain").json()
    first = chain["entries"][0]
    # Flip a single field the hash covers → the recomputed hash no longer matches.
    tampered = {**first, "recordCount": first["recordCount"] + 999}
    assert _sha256(_preimage(tampered, chain["genesis"])) != first["entryHash"]


def test_chain_grows_and_stays_verifiable_after_a_read(client: TestClient) -> None:
    before = client.get("/api/audit/chain").json()
    client.get("/api/net-worth")  # a gated read appends to the chain
    after = client.get("/api/audit/chain").json()
    assert len(after["entries"]) > len(before["entries"])
    prev = after["genesis"]
    for entry in after["entries"]:
        assert _sha256(_preimage(entry, prev)) == entry["entryHash"]
        prev = entry["entryHash"]
    assert prev == after["head"]
