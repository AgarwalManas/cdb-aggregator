"""Selective-disclosure attestation HTTP API (item-32, simulated).

Prove a derived fact — "holds at least $10,000 in liquid assets" — without
sharing the balances behind it. The aggregator computes the fact server-side and
issues a signed attestation of just the conclusion; a verifier checks the
signature. **Simulated**: signed with a symmetric demo key, not a real
zero-knowledge proof (see :mod:`app.attestation`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.demo import AggregatorState
from app.api.dto import (
    AttestationVerificationView,
    AttestationView,
    FactView,
    IssueAttestationRequest,
    VerifyAttestationRequest,
)
from app.api.session import get_state
from app.attestation import FACTS, issue, verify

router = APIRouter(prefix="/api/attestations", tags=["attestations"])

StateDep = Annotated[AggregatorState, Depends(get_state)]


def _has_income(state: AggregatorState) -> bool:
    return any(
        txn.category == "Income"
        for account in state.adapter.get_accounts()
        for txn in state.adapter.get_transactions(account.account_id)
    )


@router.get("/catalog", summary="Facts you can prove without sharing the data")
def attestation_catalog() -> list[FactView]:
    return [
        FactView(fact_id=f.fact_id, question=f.question, disclosure=f.disclosure)
        for f in FACTS.values()
    ]


@router.post("/issue", summary="Issue a signed attestation of a derived fact")
def issue_attestation(body: IssueAttestationRequest, state: StateDep) -> AttestationView:
    if body.fact_id not in FACTS:
        raise HTTPException(status_code=404, detail="unknown fact")
    att = issue(
        body.fact_id,
        subject=state.customer_id,
        accounts=state.adapter.get_accounts(),
        has_income=_has_income(state),
        now=datetime.now(UTC),
    )
    return AttestationView(**att)


@router.post("/verify", summary="Verify a presented attestation's signature")
def verify_attestation(body: VerifyAttestationRequest) -> AttestationVerificationView:
    valid, reason = verify(body.attestation.model_dump())
    return AttestationVerificationView(valid=valid, reason=reason)
