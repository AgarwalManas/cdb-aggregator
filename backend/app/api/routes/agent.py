"""Agentic delegation HTTP API (Item 11) + the activity & authority console (item-28).

Delegate a scoped, revocable task to the agent, see the delegation governing it,
revoke it one-tap, and run the intent. Running requires an **active** delegation;
without one the agent is powerless — the whole point. Every read the agent makes
while running goes through the consent gate and into the audit log, attributed to
the agent identity.

Item 28 makes that delegated authority *visible and revocable in real time*: a
live action feed (each row a logged read), an authority card (identity, scope,
time remaining, Pause / Revoke), an approval queue for the suggestion-only
actions, and an intent → scope preview shown before a grant is minted. Revoking
or pausing halts the feed immediately — ``live`` goes false and ``run`` is
refused.
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
    CashSuggestion,
    run_cash_finder,
)
from app.api.demo import DECISIONS, PENDING, AggregatorState, Approval
from app.api.dto import (
    SCOPE_CATALOG,
    AgentActivityRow,
    AgentActivityView,
    AnalyzedAccountView,
    ApprovalDecisionRequest,
    ApprovalView,
    AuthorityView,
    DelegationView,
    NotCountedView,
    ScopeInfo,
    ScopePreviewView,
    SuggestionView,
)
from app.api.session import get_state
from app.models import Consent, ConsentStatus

router = APIRouter(prefix="/api/agent", tags=["agent"])

DELEGATION_DAYS = 30

#: Raw audit actions the agent emits → a human phrase for the activity feed.
INTENTS: dict[str, str] = {
    "read_account": "Check account details",
    "read_balances": "Read current balance",
    "read_transactions": "Read transactions",
    "read_holdings": "Read investment holdings",
    "read_accounts": "List accounts",
    "read_customer": "Read identity",
}


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


def _suggestion_view(suggestion: CashSuggestion) -> SuggestionView:
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
    state.agent_paused = False  # a fresh delegation starts live, never paused
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
    now = datetime.now(UTC)
    if consent is None or not consent.is_active(now):
        # No active delegation → the agent cannot act. That's the governance.
        raise HTTPException(status_code=403, detail="no active delegation for this agent")
    if state.agent_paused:
        # Paused authority halts the agent without revoking the grant.
        raise HTTPException(status_code=409, detail="the agent is paused")

    suggestion = run_cash_finder(
        state.reader(),
        customer_id=state.customer_id,
        account_ids=consent.account_ids,
        source_label=lambda aid: (
            c.source_label if (c := state.connection_for_account(aid)) else None
        ),
    )
    state.enqueue_suggestion(suggestion, now)  # every run queues a decision
    return _suggestion_view(suggestion)


# --- Activity & authority console (item-28) ----------------------------------


def _authority_view(
    state: AggregatorState, consent: Consent | None, now: datetime
) -> AuthorityView:
    base = {
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "description": AGENT_DESCRIPTION,
        "paused": state.agent_paused,
    }
    if consent is None:
        return AuthorityView(**base, status="NONE", scopes=[], account_ids=[])
    remaining = None
    if consent.is_active(now):
        remaining = max(0, int((consent.expires_at - now).total_seconds()))
    return AuthorityView(
        **base,
        status=consent.effective_status(now).value,
        scopes=sorted(consent.scopes, key=lambda s: s.value),
        account_ids=consent.account_ids,
        created_at=consent.created_at,
        expires_at=consent.expires_at,
        revoked_at=consent.revoked_at,
        seconds_remaining=remaining,
    )


def _halted_reason(state: AggregatorState, consent: Consent | None, now: datetime) -> str:
    if consent is None:
        return "No delegation — the agent has no authority."
    if state.agent_paused and consent.is_active(now):
        return "Paused — you paused the agent. Resume to let it act again."
    status = consent.effective_status(now)
    if status is ConsentStatus.REVOKED:
        return "Revoked — the delegation was revoked, so the agent stopped."
    if status is ConsentStatus.EXPIRED:
        return "Expired — the delegation window closed."
    return "The agent has no active authority."


def _activity_rows(state: AggregatorState) -> list[AgentActivityRow]:
    rows: list[AgentActivityRow] = []
    for event in state.audit.all():
        if event.recipient != AGENT_ID:
            continue  # the feed shows only the agent's own reads
        connection = state.connection_for_account(event.account_id) if event.account_id else None
        rows.append(
            AgentActivityRow(
                occurred_at=event.occurred_at,
                intent=INTENTS.get(event.action, event.action),
                action=event.action,
                scope=event.scope,
                account_id=event.account_id,
                source_label=connection.source_label if connection else None,
                authorizing_consent_id=event.consent_id,
                allowed=event.allowed,
                status="authorized" if event.allowed else "denied",
            )
        )
    rows.reverse()  # newest first
    return rows


def _approval_view(approval: Approval) -> ApprovalView:
    return ApprovalView(
        approval_id=approval.approval_id,
        created_at=approval.created_at,
        status=approval.status,
        note=approval.note,
        decided_at=approval.decided_at,
        suggestion=_suggestion_view(approval.suggestion),
    )


@router.get("/authority", summary="The scoped authority the agent holds now")
def get_authority(state: StateDep) -> AuthorityView:
    return _authority_view(state, _current_delegation(state), datetime.now(UTC))


@router.post("/pause", summary="Pause the agent without revoking the grant")
def pause_agent(state: StateDep) -> AuthorityView:
    state.agent_paused = True
    return _authority_view(state, _current_delegation(state), datetime.now(UTC))


@router.post("/resume", summary="Let a paused agent act again")
def resume_agent(state: StateDep) -> AuthorityView:
    state.agent_paused = False
    return _authority_view(state, _current_delegation(state), datetime.now(UTC))


@router.get("/activity", summary="The agent's live action feed")
def get_activity(state: StateDep) -> AgentActivityView:
    consent = _current_delegation(state)
    now = datetime.now(UTC)
    live = consent is not None and consent.is_active(now) and not state.agent_paused
    reason = None if live else _halted_reason(state, consent, now)
    return AgentActivityView(live=live, halted_reason=reason, rows=_activity_rows(state))


@router.get("/preview", summary="Intent → scope preview before granting")
def preview_scope(state: StateDep) -> ScopePreviewView:
    account_ids = state.balance_shared_account_ids()
    required = set(REQUIRED_SCOPES)

    def info(scope) -> ScopeInfo:
        label, desc = SCOPE_CATALOG[scope]
        return ScopeInfo(scope=scope, label=label, description=desc)

    return ScopePreviewView(
        agent_name=AGENT_NAME,
        duration_days=DELEGATION_DAYS,
        account_ids=account_ids,
        account_count=len(account_ids),
        visible=[info(s) for s in SCOPE_CATALOG if s in required],
        withheld=[info(s) for s in SCOPE_CATALOG if s not in required],
    )


@router.get("/approvals", summary="The suggestion-only approval queue")
def list_approvals(state: StateDep) -> list[ApprovalView]:
    return [_approval_view(a) for a in reversed(state.approvals)]  # newest first


@router.post("/approvals/{approval_id}/decision", summary="Approve / reject / request changes")
def decide_approval(
    approval_id: str, body: ApprovalDecisionRequest, state: StateDep
) -> ApprovalView:
    approval = state.approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="no such approval")
    outcome = DECISIONS.get(body.decision.upper())
    if outcome is None:
        raise HTTPException(status_code=422, detail="unknown decision")
    if approval.status != PENDING:
        raise HTTPException(status_code=409, detail="this suggestion was already decided")
    approval.status = outcome
    approval.note = body.note
    approval.decided_at = datetime.now(UTC)
    return _approval_view(approval)
