"""Consent dashboard HTTP API (Item 9).

The endpoints the React client calls: list the available scopes, list the
customer's connections, connect a new source (grant), one-tap revoke, and read
the traceability audit log. State lives on ``app.state.aggregator`` (seeded by
:func:`app.api.demo.build_demo_state`).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.demo import SOURCES, AggregatorState, Connection
from app.api.dto import (
    AuditEventView,
    ConnectionView,
    GrantRequest,
    ScopeInfo,
    scope_catalog,
)
from app.models import Consent

router = APIRouter(prefix="/api", tags=["consent"])


def get_state(request: Request) -> AggregatorState:
    return request.app.state.aggregator


StateDep = Annotated[AggregatorState, Depends(get_state)]


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


@router.get("/audit", summary="Traceability audit log (most recent first)")
def list_audit(state: StateDep) -> list[AuditEventView]:
    events = reversed(state.audit.all())
    return [
        AuditEventView(
            occurred_at=e.occurred_at,
            action=e.action,
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
