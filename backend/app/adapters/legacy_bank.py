"""Adapter for the messy legacy bank (Item 4) → canonical model.

This is where the normalizer earns its keep. The mappers translate every quirk
the legacy source invents back into the canonical model: vocab (``chequing`` →
``CHECKING``), comma-string money, signed amounts → unsigned + ``debitCreditMemo``,
epoch-millis and ``DD/MM/YYYY`` dates, a bare lowercase currency, ``cleared`` →
status, ``positions`` → holdings, and a single ``fullName`` back into a structured
name. Transactions and holdings borrow currency/date context from their account,
since the legacy records don't carry it themselves.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from app.models import (
    Account,
    AccountCategory,
    AccountStatus,
    AccountType,
    Balance,
    BalanceType,
    Customer,
    DebitCreditMemo,
    HoldingType,
    InvestmentHolding,
    PersonName,
    PostalAddress,
    Transaction,
    TransactionStatus,
)

from .base import (
    SourceAdapter,
    SourceClient,
    normalize,
    to_decimal,
)

SOURCE_NAME = "legacy_bank"

# Legacy vocab -> canonical enums.
_KIND_TO_TYPE: dict[str, tuple[AccountCategory, AccountType]] = {
    "chequing": (AccountCategory.DEPOSIT_ACCOUNT, AccountType.CHECKING),
    "save": (AccountCategory.DEPOSIT_ACCOUNT, AccountType.SAVINGS),
    "tfsa": (AccountCategory.INVESTMENT_ACCOUNT, AccountType.TFSA),
}
_STATE_TO_STATUS: dict[str, AccountStatus] = {
    "active": AccountStatus.OPEN,
    "dormant": AccountStatus.RESTRICTED,
    "closed": AccountStatus.CLOSED,
}
_ASSET_TO_HOLDING: dict[str, HoldingType] = {
    "etf": HoldingType.ETF,
    "stock": HoldingType.EQUITY,
    "cash": HoldingType.CASH,
    "bond": HoldingType.FIXED_INCOME,
    "fund": HoldingType.MUTUAL_FUND,
}


# --- Date/format helpers (legacy-specific) -----------------------------------


def _parse_ddmmyyyy(value: str) -> datetime:
    """'29/06/2026' -> midnight UTC on that date."""
    return datetime.strptime(value, "%d/%m/%Y").replace(tzinfo=UTC)


def _parse_epoch_millis(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _parse_address(addr: str | None) -> PostalAddress | None:
    """Best-effort split of a one-line address; ``None`` if it can't be parsed.

    Normalization tolerates un-parseable *optional* data rather than failing the
    whole customer over a cosmetic field.
    """

    if not addr:
        return None
    segments = [s.strip() for s in addr.split(",")]
    if len(segments) < 3:
        return None
    middle = segments[1].split()  # e.g. ["Toronto", "ON", "M5V", "1A1"]
    if len(middle) < 3:
        return None
    return PostalAddress(
        line1=segments[0],
        city=middle[0],
        region=middle[1],
        postal_code=" ".join(middle[2:]),
        country=segments[-1],
    )


# --- Pure mappers (raw legacy dict -> canonical) -----------------------------


def map_customer(raw: dict[str, Any]) -> Customer:
    parts = raw["fullName"].split()
    first = parts[0]
    last = " ".join(parts[1:]) or parts[0]
    contact = raw.get("contact", {})
    address = _parse_address(contact.get("addr"))
    return Customer(
        customer_id=raw["custId"],
        name=PersonName(first=first, last=last),
        emails=[contact["emailAddr"]] if contact.get("emailAddr") else [],
        addresses=[address] if address else [],
    )


def map_account(raw: dict[str, Any]) -> Account:
    category, account_type = _KIND_TO_TYPE[raw["kind"]]
    currency = raw["ccy"].upper()  # "cad" -> "CAD"
    balances: list[Balance] = []
    balance = raw.get("balance", {})
    if "ledger" in balance:
        available = balance.get("available")
        balances = [
            Balance(
                as_of=_parse_ddmmyyyy(raw["asOf"]),
                currency=currency,
                current=to_decimal(balance["ledger"]),
                available=to_decimal(available) if available is not None else None,
                balance_type=BalanceType.ASSET,
            )
        ]
    return Account(
        account_id=raw["acctRef"],
        # Legacy accounts don't carry the customer id; the snapshot links them.
        customer_id=None,
        category=category,
        account_type=account_type,
        status=_STATE_TO_STATUS.get(raw["openState"], AccountStatus.OPEN),
        currency=currency,
        nickname=raw.get("label"),
        balances=balances,
    )


def map_transaction(raw: dict[str, Any], *, account_id: str, currency: str) -> Transaction:
    amount = to_decimal(raw["amt"])  # signed: negative == money out
    cleared = bool(raw.get("cleared"))
    when = _parse_epoch_millis(raw["when"])
    return Transaction(
        transaction_id=raw["id"],
        account_id=account_id,
        amount=abs(amount),
        currency=currency,
        debit_credit_memo=DebitCreditMemo.DEBIT if amount < 0 else DebitCreditMemo.CREDIT,
        status=TransactionStatus.POSTED if cleared else TransactionStatus.PENDING,
        transaction_timestamp=when,
        posted_timestamp=when if cleared else None,
        description=raw.get("narrative"),
    )


def map_holding(
    raw: dict[str, Any], *, account_id: str, currency: str, as_of: datetime
) -> InvestmentHolding:
    symbol = raw.get("sym")
    cost = raw.get("book")
    price = raw.get("last")
    market = raw.get("mktVal")
    return InvestmentHolding(
        holding_id=f"{account_id}:{symbol or raw['assetClass']}",  # positions have no id
        account_id=account_id,
        holding_type=_ASSET_TO_HOLDING.get(raw["assetClass"], HoldingType.OTHER),
        symbol=symbol,
        quantity=to_decimal(raw["qty"]),
        cost_basis=to_decimal(cost) if cost is not None else None,
        current_unit_price=to_decimal(price) if price is not None else None,
        market_value=to_decimal(market) if market is not None else None,
        currency=currency,
        as_of=as_of,  # positions carry no date; use the account's
    )


# --- Transport client --------------------------------------------------------


class LegacyHttpClient:
    """Fetches raw legacy JSON over HTTP: session login, then the nested blob.

    The blob (``/api/accounts``) is fetched once and cached, since it carries the
    accounts, their transactions, and their positions all together.
    """

    def __init__(self, http: httpx.Client, user: str, password: str) -> None:
        self._http = http
        self._user = user
        self._password = password
        self._sid: str | None = None
        self._blob: dict[str, Any] | None = None

    @classmethod
    def connect(
        cls, base_url: str, user: str, password: str, *, timeout: float = 10.0
    ) -> LegacyHttpClient:
        return cls(httpx.Client(base_url=base_url, timeout=timeout), user, password)

    def _session_headers(self) -> dict[str, str]:
        if self._sid is None:
            resp = self._http.post("/api/login", json={"user": self._user, "pass": self._password})
            resp.raise_for_status()
            self._sid = resp.json()["sid"]
        return {"X-Session-Id": self._sid}

    def _accounts_blob(self) -> dict[str, Any]:
        if self._blob is None:
            resp = self._http.get("/api/accounts", headers=self._session_headers())
            resp.raise_for_status()
            self._blob = resp.json()
        return self._blob

    def get_customer(self) -> dict[str, Any]:
        resp = self._http.get("/api/profile", headers=self._session_headers())
        resp.raise_for_status()
        return resp.json()

    def get_accounts(self) -> list[dict[str, Any]]:
        return self._accounts_blob()["accounts"]

    def get_account(self, account_id: str) -> dict[str, Any]:
        for account in self._accounts_blob()["accounts"]:
            if account["acctRef"] == account_id:
                return account
        raise KeyError(account_id)

    def get_transactions(self, account_id: str) -> list[dict[str, Any]]:
        return self.get_account(account_id).get("txns", [])

    def get_holdings(self, account_id: str) -> list[dict[str, Any]]:
        return self.get_account(account_id).get("positions", [])

    def close(self) -> None:
        self._http.close()


# --- Adapter -----------------------------------------------------------------


class LegacyBankAdapter(SourceAdapter):
    """Wires the legacy transport client to the legacy mappers."""

    source_name = SOURCE_NAME

    def __init__(self, client: SourceClient) -> None:
        self._client = client

    def get_customer(self) -> Customer:
        raw = self._client.get_customer()
        return normalize(self.source_name, "customer", raw.get("custId"), map_customer, raw)

    def get_accounts(self) -> list[Account]:
        return [
            normalize(self.source_name, "account", raw.get("acctRef"), map_account, raw)
            for raw in self._client.get_accounts()
        ]

    def get_transactions(self, account_id: str) -> list[Transaction]:
        currency = self._client.get_account(account_id)["ccy"].upper()
        return [
            normalize(
                self.source_name,
                "transaction",
                raw.get("id"),
                lambda r: map_transaction(r, account_id=account_id, currency=currency),
                raw,
            )
            for raw in self._client.get_transactions(account_id)
        ]

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        account = self._client.get_account(account_id)
        currency = account["ccy"].upper()
        as_of = _parse_ddmmyyyy(account["asOf"])
        return [
            normalize(
                self.source_name,
                "holding",
                raw.get("sym"),
                lambda r: map_holding(r, account_id=account_id, currency=currency, as_of=as_of),
                raw,
            )
            for raw in self._client.get_holdings(account_id)
        ]
