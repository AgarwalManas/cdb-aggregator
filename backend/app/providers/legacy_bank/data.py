"""Seed data for the legacy bank — deliberately messy, non-FDX shapes.

The same underlying facts as the FDX bank (so the two can later be merged), but
expressed the way a crufty legacy system would: abbreviated keys, money as
comma-formatted strings, signed transaction amounts, two different date formats
(epoch millis for transactions, ``DD/MM/YYYY`` for balance dates), a bare
lowercase currency, and everything returned as one nested blob.

This is intentionally annoying. That's the point — Item 5's adapter has to tame
it into the same canonical model the clean FDX source maps into.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    """Epoch milliseconds for a UTC instant — the legacy txn timestamp format."""
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


#: Messy customer: a single name string (not structured) and a one-line address.
PROFILE: dict[str, Any] = {
    "custId": "GBC-771",
    "fullName": "Ada Lovelace",
    "contact": {
        "emailAddr": "ada@example.com",
        "addr": "1 Analytical Way, Toronto ON M5V 1A1, CA",
    },
}

#: One nested blob: accounts each carry a nested balance, their own transactions,
#: and (for investments) positions. No separate endpoints, no FDX field names.
ACCOUNTS: list[dict[str, Any]] = [
    {
        "acctRef": "GB-CHQ-9981",
        "kind": "chequing",  # vocab: chequing / save / tfsa
        "label": "Main Chequing",
        "openState": "active",  # active / dormant / closed
        "ccy": "cad",  # bare, lowercase
        "balance": {"ledger": "4,210.55", "available": "4,100.00"},  # comma strings, nested
        "asOf": "29/06/2026",  # DD/MM/YYYY
        "txns": [
            # Signed amount (negative = money out); epoch millis; cleared flag.
            {
                "id": "T-5501",
                "amt": -85.20,
                "when": _ms(2026, 6, 27, 14, 30),
                "narrative": "LOBLAWS #1234",
                "cleared": True,
            },
            {
                "id": "T-5502",
                "amt": 2400.00,
                "when": _ms(2026, 6, 26, 12, 0),
                "narrative": "PAYROLL",
                "cleared": True,
            },
            {
                "id": "T-5503",
                "amt": -42.99,
                "when": _ms(2026, 6, 29, 9, 15),
                "narrative": "UBER EATS",
                "cleared": False,  # not cleared == pending
            },
        ],
    },
    {
        "acctRef": "GB-SAV-3310",
        "kind": "save",
        "label": "Savings",
        "openState": "active",
        "ccy": "cad",
        "balance": {"ledger": "15,800.00", "available": "15,800.00"},
        "asOf": "29/06/2026",
        "txns": [
            {
                "id": "T-6001",
                "amt": 12.33,
                "when": _ms(2026, 6, 30, 0, 0),
                "narrative": "INTEREST",
                "cleared": True,
            },
        ],
    },
    {
        "acctRef": "GB-INV-2207",
        "kind": "tfsa",
        "label": "TFSA",
        "openState": "active",
        "ccy": "cad",
        "balance": {"ledger": "11,193.50"},  # no "available" key on this one
        "asOf": "29/06/2026",
        "positions": [  # "positions", not "holdings"
            {
                "sym": "VFV",
                "assetClass": "etf",
                "qty": 50,
                "book": "4,500.00",
                "last": "110.25",
                "mktVal": "5,512.50",
            },
            {
                "sym": "SHOP",
                "assetClass": "stock",
                "qty": 12,
                "book": "1,100.00",
                "last": "98.00",
                "mktVal": "1,176.00",
            },
            {
                "sym": None,
                "assetClass": "cash",
                "qty": 1,
                "mktVal": "4,505.00",
            },  # cash, no last/book
        ],
        "txns": [
            {
                "id": "T-7001",
                "amt": 1000.00,
                "when": _ms(2026, 6, 20, 15, 0),
                "narrative": "CONTRIBUTION",
                "cleared": True,
            },
        ],
    },
]


def accounts_blob() -> dict[str, Any]:
    """The single nested response the ``/api/accounts`` endpoint returns."""
    return {"custId": PROFILE["custId"], "accounts": ACCOUNTS}
