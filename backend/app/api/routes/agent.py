"""Agentic delegation HTTP API (Item 11).

Delegate a scoped, revocable task to the agent, see the delegation governing it,
revoke it one-tap, and run the intent. Running requires an **active** delegation;
without one the agent is powerless — the whole point. Every read the agent makes
while running goes through the consent gate and into the audit log, attributed to
the agent identity.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.agent import (
    AGENT_DESCRIPTION,
    AGENT_ID,
    AGENT_NAME,
    REQUIRED_SCOPES,
    run_cash_finder,
)
from app.api.demo import AggregatorState
from app.api.dto import (
    AnalyzedAccountView,
    DelegationView,
    NotCountedView,
    SuggestionView,
)
from app.api.session import get_state
from app.models import Consent

router = APIRouter(prefix="/api/agent", tags=["agent"])

DELEGATION_DAYS = 30


StateDep = Annotated[AggregatorState, Depends(get_state)]


def _delegation_view(consent: Consent | None) -> DelegationView:
    base = {
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "description": AGENT_DESCRIPTION,
    }
    if consent is None:
        return DelegationView(**base, status="NONE", scopes=[], account_ids=[])
    return DelegationView(
        **base,
        status=consent.effective_status(datetime.now(UTC)).value,
        scopes=sorted(consent.scopes, key=lambda s: s.value),
        account_ids=consent.account_ids,
        created_at=consent.created_at,
        expires_at=consent.expires_at,
        revoked_at=consent.revoked_at,
    )


def _current_delegation(state: AggregatorState) -> Consent | None:
    if state.agent_delegation_id is None:
        return None
    return state.store.get(state.agent_delegation_id)


@router.get("/delegation", summary="The agent and its current delegation")
def get_delegation(state: StateDep) -> DelegationView:
    return _delegation_view(_current_delegation(state))


@router.post("/delegation", summary="Delegate the task to the agent")
def delegate(state: StateDep) -> DelegationView:
    # A delegation is capped at what the customer shared balances for.
    account_ids = state.balance_shared_account_ids()
    consent = state.store.grant(
        state.customer_id,
        AGENT_ID,
        REQUIRED_SCOPES,
        duration=timedelta(days=DELEGATION_DAYS),
        account_ids=account_ids,
    )
    state.agent_delegation_id = consent.consent_id
    return _delegation_view(consent)


@router.post("/delegation/revoke", summary="Revoke the agent's delegation")
def revoke_delegation(state: StateDep) -> DelegationView:
    consent = _current_delegation(state)
    if consent is None:
        raise HTTPException(status_code=404, detail="no active delegation")
    return _delegation_view(state.store.revoke(consent.consent_id))


@router.post("/run", summary="Run the delegated intent (suggestion only)")
def run(state: StateDep) -> SuggestionView:
    consent = _current_delegation(state)
    if consent is None or not consent.is_active(datetime.now(UTC)):
        # No active delegation → the agent cannot act. That's the governance.
        raise HTTPException(status_code=403, detail="no active delegation for this agent")

    suggestion = run_cash_finder(
        state.reader(),
        customer_id=state.customer_id,
        account_ids=consent.account_ids,
        source_label=lambda aid: (
            c.source_label if (c := state.connection_for_account(aid)) else None
        ),
    )
    return SuggestionView(
        idle_cash=suggestion.idle_cash,
        currency=suggestion.currency,
        estimated_annual_gain=suggestion.estimated_annual_gain,
        target_rate=suggestion.target_rate,
        threshold_rate=suggestion.threshold_rate,
        analyzed=[
            AnalyzedAccountView(
                account_id=a.account_id,
                label=a.label,
                source_label=a.source_label,
                balance=a.balance,
                rate=a.rate,
                idle=a.idle,
                estimated_gain=a.estimated_gain,
            )
            for a in suggestion.analyzed
        ],
        not_counted=[
            NotCountedView(account_id=n.account_id, reason=n.reason) for n in suggestion.not_counted
        ],
    )
