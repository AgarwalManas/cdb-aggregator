"""Aggregation HTTP API (Item 10).

The unified client view: merged accounts, the merged transaction feed, and
household net worth. All three read through the consent gate (see
:mod:`app.api.aggregation`), so what comes back is exactly what the customer has
an active, in-scope consent for.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api import aggregation
from app.api.demo import AggregatorState
from app.api.dto import AccountView, NetWorthView, TransactionView

router = APIRouter(prefix="/api", tags=["aggregation"])


def get_state(request: Request) -> AggregatorState:
    return request.app.state.aggregator


StateDep = Annotated[AggregatorState, Depends(get_state)]


@router.get("/accounts", summary="Merged accounts across connected sources")
def list_accounts(state: StateDep) -> list[AccountView]:
    return aggregation.merged_accounts(state)


@router.get("/transactions", summary="Merged transaction feed (most recent first)")
def list_transactions(state: StateDep) -> list[TransactionView]:
    return aggregation.merged_transactions(state)


@router.get("/net-worth", summary="Household net worth (consented balances only)")
def get_net_worth(state: StateDep) -> NetWorthView:
    return aggregation.net_worth(state)
