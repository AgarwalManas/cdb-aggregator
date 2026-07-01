"""Selective-disclosure attestations — prove a fact without sharing the data (item-32).

**Simulated.** This demonstrates the *pattern* of selective disclosure / zero
knowledge: the aggregator computes a derived fact from the customer's (mock) data
and issues a signed attestation of just that conclusion — the underlying balances
and transactions are never disclosed. It is **not** a real zero-knowledge proof:
the fact is computed server-side and signed with a symmetric demo key (HMAC), not
proven cryptographically. A real deployment would use SD-JWT VC / range proofs
and asymmetric issuer keys. See the in-product SIMULATION banner.

Alignment targets (not claims of conformance): W3C Verifiable Credentials, IETF
SD-JWT VC, OpenID for Verifiable Presentations.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.models import Account, BalanceType

# A demo signing key — deliberately not a secret. A real issuer would hold an
# asymmetric private key and publish the verifying key; this is a stand-in.
_DEMO_KEY = b"cdb-demo-attestation-key-not-secret"
KEY_ID = "cdb-demo-key-1"
ALGORITHM = "HMAC-SHA256 (demo)"
ISSUER = "cdb-aggregator (demo issuer)"

LIQUID_THRESHOLD = Decimal("10000")


@dataclass(frozen=True)
class Fact:
    """A provable derived fact and how it reads either way."""

    fact_id: str
    question: str
    claim_true: str
    claim_false: str
    disclosure: str  # what stays hidden — the selective-disclosure promise


FACTS: dict[str, Fact] = {
    "liquid_10k": Fact(
        fact_id="liquid_10k",
        question="Do you hold at least $10,000 in liquid assets?",
        claim_true="Holds at least $10,000 in liquid assets.",
        claim_false="Does not hold $10,000 in liquid assets.",
        disclosure="Your actual balances are never shared — only this yes/no.",
    ),
    "no_overdraft": Fact(
        fact_id="no_overdraft",
        question="Are all of your deposit accounts in good standing (non-negative)?",
        claim_true="All deposit accounts are non-negative.",
        claim_false="At least one deposit account is overdrawn.",
        disclosure="The individual balances stay hidden — only the standing is shared.",
    ),
    "salary_here": Fact(
        fact_id="salary_here",
        question="Is income deposited to an account here?",
        claim_true="Income is deposited to an account here.",
        claim_false="No income deposit was found.",
        disclosure="The amount, employer, and dates are never shared.",
    ),
}


def _liquid_assets(accounts: list[Account]) -> Decimal:
    total = Decimal("0")
    for account in accounts:
        for balance in account.balances:
            if balance.balance_type is BalanceType.ASSET:
                total += balance.current
    return total


def _all_deposits_non_negative(accounts: list[Account]) -> bool:
    return all(
        balance.current >= 0
        for account in accounts
        for balance in account.balances
        if balance.balance_type is BalanceType.ASSET
    )


def compute(fact_id: str, accounts: list[Account], *, has_income: bool) -> bool:
    """Evaluate a provable fact against the (mock) data."""
    if fact_id == "liquid_10k":
        return _liquid_assets(accounts) >= LIQUID_THRESHOLD
    if fact_id == "no_overdraft":
        return _all_deposits_non_negative(accounts)
    return has_income  # salary_here


def _payload(att: dict) -> str:
    """The canonical string the signature covers — stable across issue/verify."""
    signed = {k: att[k] for k in ("fact_id", "claim", "holds", "subject", "issuer", "issued_at")}
    return json.dumps(signed, sort_keys=True, separators=(",", ":"))


def _sign(att: dict) -> str:
    return hmac.new(_DEMO_KEY, _payload(att).encode("utf-8"), hashlib.sha256).hexdigest()


def issue(
    fact_id: str,
    *,
    subject: str,
    accounts: list[Account],
    has_income: bool,
    now: datetime,
) -> dict:
    """Compute the fact and return a signed attestation of just the conclusion."""
    fact = FACTS[fact_id]
    holds = compute(fact_id, accounts, has_income=has_income)
    att = {
        "fact_id": fact_id,
        "question": fact.question,
        "claim": fact.claim_true if holds else fact.claim_false,
        "holds": holds,
        "subject": subject,
        "issuer": ISSUER,
        "issued_at": now.isoformat(),
        "algorithm": ALGORITHM,
        "key_id": KEY_ID,
        "disclosure": fact.disclosure,
    }
    att["signature"] = _sign(att)
    return att


def verify(att: dict) -> tuple[bool, str]:
    """Recompute the signature over the presented fields — tamper-evident."""
    signature = att.get("signature")
    if not signature:
        return False, "No signature present."
    if not hmac.compare_digest(signature, _sign(att)):
        return False, "Signature does not match — the attestation was altered."
    return True, "Signature valid — issued by the demo issuer and unaltered."
