"""Seed data for the mock FDX bank, shaped like FDX API responses.

Plain dicts on purpose: this is an *external* system's wire format, not the
aggregator's canonical model. The shapes mirror FDX Core conventions worth
mapping later — a ``currency`` object (``{"currencyCode": ...}``) rather than a
bare string, balance fields carried on the account, the unsigned
``amount`` + ``debitCreditMemo`` transaction convention, and ``units`` (not
"quantity") on holdings. Amounts are JSON numbers, as a real bank would send.

One customer, three accounts (chequing, savings, a self-directed investment
account with holdings), and a handful of transactions including a pending one.
"""

from __future__ import annotations

from typing import Any

#: FDX major API version this mock speaks. Surfaced in the resource path.
FDX_API_VERSION = "v6"

CUSTOMER: dict[str, Any] = {
    "customerId": "cust-001",
    "name": {"first": "Ada", "last": "Lovelace"},
    "email": "ada@example.com",
    "addresses": [
        {
            "line1": "1 Analytical Way",
            "city": "Toronto",
            "region": "ON",
            "postalCode": "M5V 1A1",
            "country": "CA",
        }
    ],
}

#: Accounts keyed by accountId. Investment account embeds its holdings, as FDX
#: allows; balances are carried as fields on the account.
ACCOUNTS: dict[str, dict[str, Any]] = {
    "acc-chq-001": {
        "accountId": "acc-chq-001",
        "customerId": "cust-001",
        "accountCategory": "DEPOSIT_ACCOUNT",
        "accountType": "CHECKING",
        "nickname": "Everyday Chequing",
        "status": "OPEN",
        "currency": {"currencyCode": "CAD"},
        "maskedAccountNumber": "****1234",
        "balanceType": "ASSET",
        "currentBalance": 4210.55,
        "availableBalance": 4100.00,
        "balanceAsOf": "2026-06-29T08:00:00Z",
    },
    "acc-sav-001": {
        "accountId": "acc-sav-001",
        "customerId": "cust-001",
        "accountCategory": "DEPOSIT_ACCOUNT",
        "accountType": "SAVINGS",
        "nickname": "Rainy Day Savings",
        "status": "OPEN",
        "currency": {"currencyCode": "CAD"},
        "maskedAccountNumber": "****5678",
        "balanceType": "ASSET",
        "currentBalance": 15800.00,
        "availableBalance": 15800.00,
        "balanceAsOf": "2026-06-29T08:00:00Z",
    },
    "acc-inv-001": {
        "accountId": "acc-inv-001",
        "customerId": "cust-001",
        "accountCategory": "INVESTMENT_ACCOUNT",
        "accountType": "BROKERAGE",
        "nickname": "Self-Directed TFSA",
        "status": "OPEN",
        "currency": {"currencyCode": "CAD"},
        "maskedAccountNumber": "****9012",
        "balanceType": "ASSET",
        "currentBalance": 11193.50,
        "balanceAsOf": "2026-06-29T08:00:00Z",
        "holdings": [
            {
                "holdingId": "hold-001",
                "holdingType": "ETF",
                "symbol": "VFV",
                "units": 50,
                "costBasis": 4500.00,
                "currentUnitPrice": 110.25,
                "marketValue": 5512.50,
                "currency": {"currencyCode": "CAD"},
                "asOf": "2026-06-29T08:00:00Z",
            },
            {
                "holdingId": "hold-002",
                "holdingType": "EQUITY",
                "symbol": "SHOP",
                "units": 12,
                "costBasis": 1100.00,
                "currentUnitPrice": 98.00,
                "marketValue": 1176.00,
                "currency": {"currencyCode": "CAD"},
                "asOf": "2026-06-29T08:00:00Z",
            },
            {
                "holdingId": "hold-003",
                "holdingType": "CASH",
                "symbol": None,
                "units": 4505.00,
                "currentUnitPrice": 1.00,
                "marketValue": 4505.00,
                "currency": {"currencyCode": "CAD"},
                "asOf": "2026-06-29T08:00:00Z",
            },
        ],
    },
}

#: Transactions keyed by accountId. Note the FDX convention: ``amount`` is an
#: unsigned magnitude; ``debitCreditMemo`` carries the direction. The pending
#: transaction deliberately has no ``postedTimestamp``.
TRANSACTIONS: dict[str, list[dict[str, Any]]] = {
    "acc-chq-001": [
        {
            "transactionId": "txn-1001",
            "accountId": "acc-chq-001",
            "amount": 85.20,
            "debitCreditMemo": "DEBIT",
            "status": "POSTED",
            "transactionTimestamp": "2026-06-27T14:30:00Z",
            "postedTimestamp": "2026-06-28T02:00:00Z",
            "description": "LOBLAWS #1234",
            "category": "Groceries",
        },
        {
            "transactionId": "txn-1002",
            "accountId": "acc-chq-001",
            "amount": 2400.00,
            "debitCreditMemo": "CREDIT",
            "status": "POSTED",
            "transactionTimestamp": "2026-06-26T12:00:00Z",
            "postedTimestamp": "2026-06-26T12:05:00Z",
            "description": "PAYROLL DEPOSIT",
            "category": "Income",
        },
        {
            "transactionId": "txn-1003",
            "accountId": "acc-chq-001",
            "amount": 42.99,
            "debitCreditMemo": "DEBIT",
            "status": "PENDING",
            "transactionTimestamp": "2026-06-29T09:15:00Z",
            "description": "UBER EATS",
            "category": "Restaurants",
        },
    ],
    "acc-sav-001": [
        {
            "transactionId": "txn-2001",
            "accountId": "acc-sav-001",
            "amount": 12.33,
            "debitCreditMemo": "CREDIT",
            "status": "POSTED",
            "transactionTimestamp": "2026-06-30T00:00:00Z",
            "postedTimestamp": "2026-06-30T00:00:00Z",
            "description": "INTEREST PAID",
            "category": "Interest",
        },
    ],
    "acc-inv-001": [
        {
            "transactionId": "txn-3001",
            "accountId": "acc-inv-001",
            "amount": 1000.00,
            "debitCreditMemo": "CREDIT",
            "status": "POSTED",
            "transactionTimestamp": "2026-06-20T15:00:00Z",
            "postedTimestamp": "2026-06-20T15:00:00Z",
            "description": "TFSA CONTRIBUTION",
            "category": "Transfer",
        },
    ],
}


def account_summary(account: dict[str, Any]) -> dict[str, Any]:
    """An account without its embedded ``holdings`` — the list-view projection.

    FDX's "get accounts" returns lighter summaries than "get account detail";
    holdings only come back on the detail call.
    """

    return {k: v for k, v in account.items() if k != "holdings"}
