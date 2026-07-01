"""The Idle-Cash Finder — a delegated intent that suggests, never acts.

Given a delegation, it reads the customer's deposit accounts **through the
consent gate** (as the agent identity, so every read is logged against the
agent), finds cash sitting in low-interest accounts above a sensible buffer, and
estimates what a higher-yield move could earn. It returns a suggestion; it moves
nothing.

The analysis is deterministic and unit-tested. The interesting part isn't the
arithmetic — it's that the agent is bound by exactly the same consent, scope,
coverage, minimization, and audit rules as any other reader. Swap this engine for
an LLM later and the governance is unchanged.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.consent import ConsentDenied
from app.consent.reader import ConsentEnforcingReader
from app.models import AccountType, ConsentScope

# --- Agent identity ----------------------------------------------------------

AGENT_ID = "agent:cash-finder"
AGENT_NAME = "Idle-Cash Finder"
AGENT_DESCRIPTION = (
    "Finds cash sitting in low-interest accounts and estimates what a higher-yield "
    "move could earn. It only reads what you delegate, and it suggests — it never moves money."
)

#: What the agent needs to do its job. The customer delegates (at most) this.
REQUIRED_SCOPES: tuple[ConsentScope, ...] = (
    ConsentScope.ACCOUNT_DETAILS,
    ConsentScope.BALANCES,
)

# --- Analysis assumptions ----------------------------------------------------

#: Assumed current yield by deposit account type (annualized).
DEPOSIT_RATES: dict[AccountType, Decimal] = {
    AccountType.CHECKING: Decimal("0.001"),  # 0.1%
    AccountType.SAVINGS: Decimal("0.005"),  # 0.5%
}
#: Cash to leave in place (e.g. for day-to-day spending) before counting idle.
BUFFERS: dict[AccountType, Decimal] = {AccountType.CHECKING: Decimal("2000")}
THRESHOLD_RATE = Decimal("0.01")  # "earning under 1%"
TARGET_RATE = Decimal("0.0275")  # a plausible high-interest option


@dataclass(frozen=True)
class AnalyzedAccount:
    account_id: str
    label: str
    source_label: str | None
    balance: Decimal
    rate: Decimal
    idle: Decimal
    estimated_gain: Decimal


@dataclass(frozen=True)
class NotCounted:
    account_id: str
    reason: str


@dataclass
class CashSuggestion:
    idle_cash: Decimal
    currency: str
    estimated_annual_gain: Decimal
    target_rate: Decimal
    threshold_rate: Decimal
    analyzed: list[AnalyzedAccount] = field(default_factory=list)
    not_counted: list[NotCounted] = field(default_factory=list)


def run_cash_finder(
    reader: ConsentEnforcingReader,
    *,
    customer_id: str,
    account_ids: list[str],
    source_label: Callable[[str], str | None],
    at: datetime | None = None,
) -> CashSuggestion:
    """Analyze the delegated accounts and return a suggestion (no side effects)."""
    idle_total = Decimal("0")
    gain_total = Decimal("0")
    currency = "CAD"
    analyzed: list[AnalyzedAccount] = []
    not_counted: list[NotCounted] = []

    for account_id in account_ids:
        try:
            account = reader.read_account(customer_id, AGENT_ID, account_id, at=at)
        except ConsentDenied:
            not_counted.append(NotCounted(account_id, "not permitted by delegation"))
            continue

        rate = DEPOSIT_RATES.get(account.account_type)
        if rate is None:
            continue  # not a cash/deposit account — nothing to optimize here

        try:
            balances = reader.read_balances(customer_id, AGENT_ID, account_id, at=at)
        except ConsentDenied:
            not_counted.append(NotCounted(account_id, "balance not delegated"))
            continue
        if not balances:
            not_counted.append(NotCounted(account_id, "no balance available"))
            continue

        balance = balances[0]
        currency = balance.currency
        buffer = BUFFERS.get(account.account_type, Decimal("0"))
        idle = max(Decimal("0"), balance.current - buffer)
        if rate >= THRESHOLD_RATE or idle <= 0:
            continue

        gain = (idle * (TARGET_RATE - rate)).quantize(Decimal("0.01"))
        idle_total += idle
        gain_total += gain
        analyzed.append(
            AnalyzedAccount(
                account_id=account_id,
                label=account.nickname or account.account_type.value,
                source_label=source_label(account_id),
                balance=balance.current,
                rate=rate,
                idle=idle,
                estimated_gain=gain,
            )
        )

    return CashSuggestion(
        idle_cash=idle_total,
        currency=currency,
        estimated_annual_gain=gain_total,
        target_rate=TARGET_RATE,
        threshold_rate=THRESHOLD_RATE,
        analyzed=analyzed,
        not_counted=not_counted,
    )
