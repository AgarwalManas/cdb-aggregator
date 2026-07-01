"""Consent dashboard HTTP API (Item 9).

The endpoints the React client calls: list the available scopes, list the
customer's connections, connect a new source (grant), one-tap revoke, and read
the traceability audit log. State is the current visitor's demo world, resolved
per session by :func:`app.api.session.get_state`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.api.demo import SOURCES, AggregatorState, Connection
from app.api.dto import (
    AuditEventView,
    ChainVerificationView,
    ConnectionView,
    GrantRequest,
    ScopeInfo,
    scope_catalog,
)
from app.api.session import SessionStore, get_state
from app.models import Consent

router = APIRouter(prefix="/api", tags=["consent"])


StateDep = Annotated[AggregatorState, Depends(get_state)]


@router.post("/demo/reset", status_code=204, summary="Reset this visitor's demo data")
def reset_demo(request: Request) -> Response:
    """Rebuild the current session's demo world, undoing any revokes/grants/runs."""
    sessions: SessionStore = request.app.state.sessions
    sessions.reset(request.state.session_id)
    return Response(status_code=204)


def _view(state: AggregatorState, connection: Connection, consent: Consent) -> ConnectionView:
    now = datetime.now(UTC)
    return ConnectionView(
        connection_id=connection.connection_id,
        source_id=connection.source_id,
        source_label=connection.source_label,
        status=consent.effective_status(now).value,
        scopes=sorted(consent.scopes, key=lambda s: s.value),
        account_ids=consent.account_ids,
        created_at=consent.created_at,
        expires_at=consent.expires_at,
        revoked_at=consent.revoked_at,
    )


@router.get("/scopes", summary="Available consent scopes")
def list_scopes() -> list[ScopeInfo]:
    return scope_catalog()


@router.get("/sources", summary="Connectable data sources")
def list_sources() -> list[dict[str, str]]:
    return [{"sourceId": sid, "sourceLabel": label} for sid, label in SOURCES.items()]


@router.get("/connections", summary="List the customer's connections")
def list_connections(state: StateDep) -> list[ConnectionView]:
    views: list[ConnectionView] = []
    for connection in state.connections:
        consent = state.store.get(connection.connection_id)
        if consent is not None:
            views.append(_view(state, connection, consent))
    return views


@router.post("/connections", status_code=201, summary="Connect a source (grant consent)")
def create_connection(body: GrantRequest, state: StateDep) -> ConnectionView:
    if body.source_id not in SOURCES:
        raise HTTPException(status_code=422, detail=f"unknown source {body.source_id!r}")
    if not body.scopes:
        raise HTTPException(status_code=422, detail="at least one scope is required")

    connection_id = state.next_connection_id()
    consent = state.store.grant(
        state.customer_id,
        state.recipient,
        body.scopes,
        duration=timedelta(days=body.duration_days),
        account_ids=body.account_ids,
        consent_id=connection_id,
    )
    connection = Connection(connection_id, body.source_id, SOURCES[body.source_id])
    state.connections.append(connection)
    return _view(state, connection, consent)


@router.post("/connections/{connection_id}/revoke", summary="One-tap revoke")
def revoke_connection(connection_id: str, state: StateDep) -> ConnectionView:
    connection = next((c for c in state.connections if c.connection_id == connection_id), None)
    if connection is None or state.store.get(connection_id) is None:
        raise HTTPException(status_code=404, detail=f"no connection {connection_id!r}")
    consent = state.store.revoke(connection_id)
    return _view(state, connection, consent)


#: The full log is append-only and grows without bound; the API returns a recent
#: window (a real UI would paginate). Every event stays in the underlying log.
AUDIT_PAGE_SIZE = 50


@router.get("/audit", summary="Traceability audit log (most recent first)")
def list_audit(state: StateDep) -> list[AuditEventView]:
    events = list(reversed(state.audit.all()))[:AUDIT_PAGE_SIZE]
    return [
        AuditEventView(
            occurred_at=e.occurred_at,
            action=e.action,
            recipient=e.recipient,
            scope=e.scope,
            account_id=e.account_id,
            allowed=e.allowed,
            reason=e.reason.value if e.reason else None,
            consent_id=e.consent_id,
            record_count=e.record_count,
            withheld=list(e.withheld),
        )
        for e in events
    ]


@router.get("/audit/verify", summary="Verify the audit log's tamper-evident hash chain")
def verify_audit(state: StateDep) -> ChainVerificationView:
    """Re-walk the hash chain and report whether the trail is intact."""
    result = state.audit.verify()
    return ChainVerificationView(
        valid=result.valid, checked=result.checked, broken_at=result.broken_at
    )
