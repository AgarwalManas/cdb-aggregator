"""Portable alias + consent-gated resolver HTTP API (item-31).

Route on a lookup, not on the identifier. The user owns a bank-neutral handle
(``ada.cdb``); resolving it returns a one-time routing token — never the raw
institution / transit / account — and only when an active, in-scope consent
covers the target. Re-pointing the alias to a different source is a scoped,
logged event. Every resolution, allowed or denied, lands in the traceability
trail. See :mod:`app.alias.resolver` for the honest-scope note (mock addressing;
no settlement).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.alias import coordinates_for
from app.api.demo import ALIAS_HANDLE, AggregatorState
from app.api.dto import (
    AliasResolutionRow,
    AliasTargetView,
    AliasView,
    ExchangeRequest,
    RepointRequest,
    ResolutionView,
    ResolveRequest,
    RoutingCoordinatesView,
)
from app.api.session import get_state
from app.models import ConsentScope

router = APIRouter(prefix="/api/alias", tags=["alias"])

StateDep = Annotated[AggregatorState, Depends(get_state)]


def _target(state: AggregatorState, account_id: str) -> AliasTargetView:
    connection = state.connection_for_account(account_id)
    label = connection.source_label if connection else "unknown"
    coords = coordinates_for(account_id, label)
    return AliasTargetView(
        account_id=account_id, source_label=label, display=f"{label} {coords.masked_account}"
    )


def _options(state: AggregatorState) -> list[AliasTargetView]:
    """The connected accounts the alias can point at — an active detail grant each."""
    seen: list[str] = []
    out: list[AliasTargetView] = []
    for connection in state.connections:
        consent = state.store.get(connection.connection_id)
        # Only an active grant that shares account details can be a routing target.
        if (
            consent is None
            or not consent.is_active()
            or ConsentScope.ACCOUNT_DETAILS not in consent.scopes
        ):
            continue
        for account_id in consent.account_ids:
            if account_id not in seen:
                seen.append(account_id)
                out.append(_target(state, account_id))
    return out


def _alias_view(state: AggregatorState) -> AliasView:
    alias = state.aliases.get(ALIAS_HANDLE)
    history = [
        AliasResolutionRow(
            occurred_at=e.occurred_at,
            requester=e.recipient,
            allowed=e.allowed,
            disclosed="one-time routing token" if e.allowed else "nothing",
            reason=e.reason.value if e.reason else None,
        )
        for e in reversed(state.resolver.resolutions())
    ]
    return AliasView(
        handle=alias.handle,
        target=_target(state, alias.account_id),
        created_at=alias.created_at,
        repointed_at=alias.repointed_at,
        options=_options(state),
        history=history,
    )


@router.get("", summary="The portable-address card")
def get_alias(state: StateDep) -> AliasView:
    return _alias_view(state)


@router.post("/resolve", summary="Resolve the alias (as a counterparty would)")
def resolve_alias(body: ResolveRequest, state: StateDep) -> ResolutionView:
    res = state.resolver.resolve(ALIAS_HANDLE, requester=body.requester)
    return ResolutionView(
        allowed=res.allowed,
        handle=res.handle,
        routing_token=res.routing_token,
        disclosed=res.disclosed,
        reason=res.reason,
    )


@router.post("/exchange", summary="Redeem a routing token for coordinates (once)")
def exchange_token(body: ExchangeRequest, state: StateDep) -> RoutingCoordinatesView:
    coords = state.resolver.exchange(body.token)
    if coords is None:
        raise HTTPException(status_code=410, detail="token is unknown, already used, or expired")
    return RoutingCoordinatesView(
        institution=coords.institution,
        transit=coords.transit,
        masked_account=coords.masked_account,
        source_label=coords.source_label,
    )


@router.post("/repoint", summary="Point the alias at a different connected account")
def repoint_alias(body: RepointRequest, state: StateDep) -> AliasView:
    alias = state.resolver.repoint(ALIAS_HANDLE, body.account_id)
    if alias is None:
        raise HTTPException(
            status_code=400, detail="that account isn't connected — the alias can't route to it"
        )
    return _alias_view(state)
