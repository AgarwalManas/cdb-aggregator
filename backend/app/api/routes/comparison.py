"""Old-way vs new-way contrast API (Item 6 / item-20).

Exposes the structured screen-scraping vs FDX comparison so the client can render
the "why FDX" visual. This is static talking-point content, not customer data, so
it doesn't pass through the consent gate.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.dto import ComparisonRow
from app.comparison import COMPARISON

router = APIRouter(prefix="/api", tags=["comparison"])


@router.get("/comparison", summary="Screen-scraping vs FDX, dimension by dimension")
def list_comparison() -> list[ComparisonRow]:
    return [
        ComparisonRow(
            dimension=c.dimension,
            screen_scraping=c.screen_scraping,
            fdx_open_banking=c.fdx_open_banking,
        )
        for c in COMPARISON
    ]
