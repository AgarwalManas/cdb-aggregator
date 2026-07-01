"""Adapter for the mock FDX bank (Item 3) → canonical model.

The clean, standards-native source, so the mappers are near-mechanical: rename a
few fields, unwrap the FDX ``currency`` object, and thread the account's currency
onto transactions (FDX carries it on the account, not the transaction). The
contrast with :mod:`app.adapters.legacy_bank` is the point — this is what a
well-shaped source costs the normalizer, versus what a messy one does.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.models import (
    Account,
    Balance,
    Customer,
    InvestmentHolding,
    PersonName,
    PostalAddress,
    Transaction,
)

from .base import (
    SourceAdapter,
    SourceClient,
    normalize,
    parse_iso8601,
    to_decimal,
)

SOURCE_NAME = "mock_fdx_bank"


# --- Pure mappers (raw FDX dict -> canonical) --------------------------------


def map_address(raw: dict[str, Any]) -> PostalAddress:
    return PostalAddress(
        line1=raw["line1"],
        city=raw["city"],
        postal_code=raw["postalCode"],
        country=raw["country"],
        region=raw.get("region"),
    )


def map_customer(raw: dict[str, Any]) -> Customer:
    name = raw["name"]
    return Customer(
        customer_id=raw["customerId"],
        name=PersonName(first=name["first"], last=name["last"]),
        emails=[raw["email"]] if raw.get("email") else [],
        addresses=[map_address(a) for a in raw.get("addresses", [])],
    )


def map_balance(raw: dict[str, Any]) -> Balance:
    available = raw.get("availableBalance")
    return Balance(
        as_of=parse_iso8601(raw["balanceAsOf"]),
        currency=raw["currency"]["currencyCode"],
        current=to_decimal(raw["currentBalance"]),
        available=to_decimal(available) if available is not None else None,
        balance_type=raw.get("balanceType", "ASSET"),
    )


def map_account(raw: dict[str, Any]) -> Account:
    return Account(
        account_id=raw["accountId"],
        customer_id=raw.get("customerId"),
        category=raw["accountCategory"],
        account_type=raw["accountType"],
        status=raw.get("status", "OPEN"),
        currency=raw["currency"]["currencyCode"],
        nickname=raw.get("nickname"),
        masked_number=raw.get("maskedAccountNumber"),
        balances=[map_balance(raw)] if "currentBalance" in raw else [],
    )


def map_transaction(raw: dict[str, Any], *, currency: str) -> Transaction:
    posted = raw.get("postedTimestamp")
    return Transaction(
        transaction_id=raw["transactionId"],
        account_id=raw["accountId"],
        amount=to_decimal(raw["amount"]),
        currency=currency,  # FDX carries currency on the account, not the txn
        debit_credit_memo=raw["debitCreditMemo"],
        status=raw.get("status", "POSTED"),
        transaction_timestamp=parse_iso8601(raw["transactionTimestamp"]),
        posted_timestamp=parse_iso8601(posted) if posted else None,
        description=raw.get("description"),
        category=raw.get("category"),
        memo=raw.get("memo"),
    )


def map_holding(raw: dict[str, Any], *, account_id: str) -> InvestmentHolding:
    price = raw.get("currentUnitPrice")
    cost = raw.get("costBasis")
    market = raw.get("marketValue")
    return InvestmentHolding(
        holding_id=raw["holdingId"],
        account_id=account_id,
        holding_type=raw["holdingType"],
        symbol=raw.get("symbol"),
        quantity=to_decimal(raw["units"]),  # FDX: "units", canonical: "quantity"
        cost_basis=to_decimal(cost) if cost is not None else None,
        current_unit_price=to_decimal(price) if price is not None else None,
        market_value=to_decimal(market) if market is not None else None,
        currency=raw["currency"]["currencyCode"],
        as_of=parse_iso8601(raw["asOf"]),
    )


# --- Transport client --------------------------------------------------------


class FdxHttpClient:
    """Fetches raw FDX JSON over HTTP, handling the OAuth2 client-credentials flow.

    Accepts any ``httpx.Client`` (a real one via :meth:`connect`, or a Starlette
    ``TestClient`` in tests) so transport can be exercised in-process.
    """

    def __init__(self, http: httpx.Client, client_id: str, client_secret: str) -> None:
        self._http = http
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None

    @classmethod
    def connect(
        cls, base_url: str, client_id: str, client_secret: str, *, timeout: float = 10.0
    ) -> FdxHttpClient:
        return cls(httpx.Client(base_url=base_url, timeout=timeout), client_id, client_secret)

    def _auth_headers(self) -> dict[str, str]:
        if self._token is None:
            resp = self._http.post(
                "/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, path: str) -> Any:
        resp = self._http.get(path, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()

    def get_customer(self) -> dict[str, Any]:
        return self._get("/fdx/v6/customers/current")

    def get_accounts(self) -> list[dict[str, Any]]:
        return self._get("/fdx/v6/accounts")["accounts"]

    def get_account(self, account_id: str) -> dict[str, Any]:
        return self._get(f"/fdx/v6/accounts/{account_id}")

    def get_transactions(self, account_id: str) -> list[dict[str, Any]]:
        return self._get(f"/fdx/v6/accounts/{account_id}/transactions")["transactions"]

    def get_holdings(self, account_id: str) -> list[dict[str, Any]]:
        return self.get_account(account_id).get("holdings", [])

    def close(self) -> None:
        self._http.close()


# --- Adapter -----------------------------------------------------------------


class FdxBankAdapter(SourceAdapter):
    """Wires the FDX transport client to the FDX mappers."""

    source_name = SOURCE_NAME

    def __init__(self, client: SourceClient) -> None:
        self._client = client

    def get_customer(self) -> Customer:
        raw = self._client.get_customer()
        return normalize(self.source_name, "customer", raw.get("customerId"), map_customer, raw)

    def get_accounts(self) -> list[Account]:
        return [
            normalize(self.source_name, "account", raw.get("accountId"), map_account, raw)
            for raw in self._client.get_accounts()
        ]

    def get_transactions(self, account_id: str) -> list[Transaction]:
        currency = self._client.get_account(account_id)["currency"]["currencyCode"]
        return [
            normalize(
                self.source_name,
                "transaction",
                raw.get("transactionId"),
                lambda r: map_transaction(r, currency=currency),
                raw,
            )
            for raw in self._client.get_transactions(account_id)
        ]

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        return [
            normalize(
                self.source_name,
                "holding",
                raw.get("holdingId"),
                lambda r: map_holding(r, account_id=account_id),
                raw,
            )
            for raw in self._client.get_holdings(account_id)
        ]
