"""Agentic delegation / intent layer (Item 11, differentiator A).

Delegating a task to an AI agent is, in this architecture, just another consent —
from the customer to an *agent identity* — that is scoped, time-limited,
revocable, and whose every data access runs through the same gate and lands in
the same audit log. That maps one-to-one onto FDX's April-2026 Agentic-AI focus
areas (agent identity, consent delegation, data minimization, downstream
accountability, traceability), and it reuses the Item 7/8 machinery wholesale.

The bundled agent — the :mod:`~app.agent.cash_finder` — reads only what it was
delegated and returns a **suggestion, not an action** (no write access), which
keeps it honest about Canada's Phase-2 (write) open-banking timing.
"""

from __future__ import annotations

from .cash_finder import (
    AGENT_DESCRIPTION,
    AGENT_ID,
    AGENT_NAME,
    REQUIRED_SCOPES,
    CashSuggestion,
    run_cash_finder,
)

__all__ = [
    "AGENT_ID",
    "AGENT_NAME",
    "AGENT_DESCRIPTION",
    "REQUIRED_SCOPES",
    "CashSuggestion",
    "run_cash_finder",
]
