"""Access receipts + permission simulation HTTP API (item-29).

``GET /api/receipts`` reshapes the traceability log into consumer-legible
receipts (also the machine-readable export the client downloads). ``POST
/api/permission-simulation`` previews, before granting, which fields a candidate
scope set would expose vs withhold.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.demo import AggregatorState
from app.api.dto import PermissionSimulationRequest, PermissionSimulationView, ReceiptView
from app.api.receipts import build_receipts, simulate_permission
from app.api.session import get_state

router = APIRouter(prefix="/api", tags=["receipts"])

StateDep = Annotated[AggregatorState, Depends(get_state)]


@router.get("/receipts", summary="Access receipts (the audit log, made legible)")
def list_receipts(state: StateDep) -> list[ReceiptView]:
    return build_receipts(state.audit.all())


@router.post("/permission-simulation", summary="Preview a candidate scope set before granting")
def simulate(body: PermissionSimulationRequest) -> PermissionSimulationView:
    visible, withheld = simulate_permission(body.scopes)
    return PermissionSimulationView(scopes=body.scopes, visible=visible, withheld=withheld)
