"""Screen-scraping adapter (Item 6) → canonical model.

The "old way": there's no API, so the transport client logs in with the user's
real credentials, pulls the HTML statement, and **parses it** into raw dicts;
the adapter then maps those into the same canonical model as every other source.

Two things this makes visible:

* **Fragility.** The parser depends on the page's structure (a ``p.balance``
  here, a ``table.txns`` there). When the bank restyles its site, the selectors
  miss and scraping breaks — see ``parse_accounts`` raising and the fragility
  test. A versioned API contract doesn't have this failure mode.
* **Scarcity.** A statement exposes far less than FDX: no stable transaction
  ids (we synthesize them), no pending flag (everything reads as posted), no
  holdings, and only a display name for the customer.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.models import (
    Account,
    AccountCategory,
    AccountType,
    Balance,
    BalanceType,
    Customer,
    DebitCreditMemo,
    InvestmentHolding,
    PersonName,
    Transaction,
    TransactionStatus,
)

from .base import SourceAdapter, normalize, to_decimal

SOURCE_NAME = "scraper_bank"

_NAME_TO_TYPE: dict[str, tuple[AccountCategory, AccountType]] = {
    "Chequing": (AccountCategory.DEPOSIT_ACCOUNT, AccountType.CHECKING),
    "Checking": (AccountCategory.DEPOSIT_ACCOUNT, AccountType.CHECKING),
    "Savings": (AccountCategory.DEPOSIT_ACCOUNT, AccountType.SAVINGS),
}

_BALANCE_RE = re.compile(r"\$([\d,]+\.\d{2})\s+([A-Z]{3})")


# --- HTML parsing (the fragile part) -----------------------------------------


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _text_after_colon(text: str) -> str:
    return text.split(":", 1)[-1].strip()


def parse_statement_date(html: str) -> str:
    node = _soup(html).select_one("p.statement-date")
    if node is None:
        raise ValueError("statement date not found (layout changed?)")
    return _text_after_colon(node.get_text())


def parse_customer(html: str) -> dict[str, Any]:
    node = _soup(html).select_one("p.acct-holder")
    if node is None:
        raise ValueError("account holder not found (layout changed?)")
    return {"holder": _text_after_colon(node.get_text())}


def parse_accounts(html: str) -> list[dict[str, Any]]:
    soup = _soup(html)
    as_of = parse_statement_date(html)
    accounts: list[dict[str, Any]] = []
    for div in soup.select("div.account"):
        heading = div.select_one("h2")
        balance_node = div.select_one("p.balance")
        if heading is None or balance_node is None:
            raise ValueError("account block missing heading/balance (layout changed?)")
        match = _BALANCE_RE.search(balance_node.get_text())
        if match is None:
            raise ValueError(f"could not parse balance from {balance_node.get_text()!r}")
        accounts.append(
            {
                "masked": div.get("data-acct"),
                "name": heading.get_text().split("(")[0].strip(),
                "balance": match.group(1),
                "currency": match.group(2),
                "asOf": as_of,
            }
        )
    if not accounts:
        raise ValueError("no accounts found on statement (layout changed?)")
    return accounts


def parse_transactions(html: str, masked: str) -> list[dict[str, Any]]:
    div = _soup(html).select_one(f'div.account[data-acct="{masked}"]')
    if div is None:
        raise ValueError(f"no account block for {masked!r}")
    table = div.select_one("table.txns")
    if table is None:
        return []  # an account can legitimately have no transactions shown
    txns: list[dict[str, Any]] = []
    index = 0
    for row in table.select("tr"):
        cells = row.select("td")
        if not cells:
            continue  # header row
        txns.append(
            {
                "date": cells[0].get_text().strip(),
                "desc": cells[1].get_text().strip(),
                "amount": cells[2].get_text().strip(),
                "masked": masked,
                "index": index,
            }
        )
        index += 1
    return txns


# --- Mappers (raw scraped dict -> canonical) ---------------------------------


def _scraped_amount(text: str) -> tuple[bool, Decimal]:
    """'-$85.20' -> (True, 85.20); '$2,400.00' -> (False, 2400.00)."""
    negative = text.strip().startswith("-")
    # to_decimal strips '$' and ',' but keeps the sign; canonical amount is unsigned.
    return negative, abs(to_decimal(text))


def map_customer(raw: dict[str, Any]) -> Customer:
    parts = raw["holder"].split()
    first = parts[0]
    last = " ".join(parts[1:]) or parts[0]
    slug = raw["holder"].lower().replace(" ", "-")
    return Customer(customer_id=f"scraped-{slug}", name=PersonName(first=first, last=last))


def map_account(raw: dict[str, Any]) -> Account:
    if raw["name"] not in _NAME_TO_TYPE:
        raise ValueError(f"unrecognized account name on statement: {raw['name']!r}")
    category, account_type = _NAME_TO_TYPE[raw["name"]]
    as_of = datetime.strptime(raw["asOf"], "%Y-%m-%d").replace(tzinfo=UTC)
    return Account(
        account_id=raw["masked"],  # the masked number is all a scrape gives us
        customer_id=None,
        category=category,
        account_type=account_type,
        currency=raw["currency"],
        nickname=raw["name"],
        masked_number=raw["masked"],
        balances=[
            Balance(
                as_of=as_of,
                currency=raw["currency"],
                current=to_decimal(raw["balance"]),
                balance_type=BalanceType.ASSET,
            )
        ],
    )


def map_transaction(raw: dict[str, Any], *, account_id: str, currency: str) -> Transaction:
    negative, amount = _scraped_amount(raw["amount"])
    when = datetime.strptime(raw["date"], "%Y-%m-%d").replace(tzinfo=UTC)
    return Transaction(
        # No stable id on a statement — synthesize a deterministic one.
        transaction_id=f"{account_id}-{raw['index']}",
        account_id=account_id,
        amount=amount,
        currency=currency,
        debit_credit_memo=DebitCreditMemo.DEBIT if negative else DebitCreditMemo.CREDIT,
        status=TransactionStatus.POSTED,  # a statement can't tell you what's pending
        transaction_timestamp=when,
        posted_timestamp=when,
        description=raw["desc"],
    )


# --- Transport client --------------------------------------------------------


class HtmlStatementClient:
    """Logs in with the customer's credentials and scrapes the HTML statement.

    The statement page is fetched once (cookies carry the session on the shared
    ``httpx.Client``) and parsed on demand.
    """

    def __init__(self, http: httpx.Client, username: str, password: str) -> None:
        self._http = http
        self._username = username
        self._password = password
        self._html: str | None = None

    @classmethod
    def connect(
        cls, base_url: str, username: str, password: str, *, timeout: float = 10.0
    ) -> HtmlStatementClient:
        return cls(httpx.Client(base_url=base_url, timeout=timeout), username, password)

    def _statement(self) -> str:
        if self._html is None:
            login = self._http.post(
                "/login", data={"username": self._username, "password": self._password}
            )
            login.raise_for_status()  # 401 on bad credentials
            page = self._http.get("/statement")
            page.raise_for_status()
            self._html = page.text
        return self._html

    def get_customer(self) -> dict[str, Any]:
        return parse_customer(self._statement())

    def get_accounts(self) -> list[dict[str, Any]]:
        return parse_accounts(self._statement())

    def get_account(self, account_id: str) -> dict[str, Any]:
        for account in parse_accounts(self._statement()):
            if account["masked"] == account_id:
                return account
        raise KeyError(account_id)

    def get_transactions(self, account_id: str) -> list[dict[str, Any]]:
        return parse_transactions(self._statement(), account_id)

    def get_holdings(self, account_id: str) -> list[dict[str, Any]]:
        return []  # statements don't show holdings — part of the "old way" scarcity

    def close(self) -> None:
        self._http.close()


# --- Adapter -----------------------------------------------------------------


class ScraperBankAdapter(SourceAdapter):
    """Same canonical interface as the API sources, backed by HTML scraping."""

    source_name = SOURCE_NAME

    def __init__(self, client: HtmlStatementClient) -> None:
        self._client = client

    def get_customer(self) -> Customer:
        raw = self._client.get_customer()
        return normalize(self.source_name, "customer", raw.get("holder"), map_customer, raw)

    def get_accounts(self) -> list[Account]:
        return [
            normalize(self.source_name, "account", raw.get("masked"), map_account, raw)
            for raw in self._client.get_accounts()
        ]

    def get_transactions(self, account_id: str) -> list[Transaction]:
        currency = self._client.get_account(account_id)["currency"]
        return [
            normalize(
                self.source_name,
                "transaction",
                f"{account_id}-{raw.get('index')}",
                lambda r: map_transaction(r, account_id=account_id, currency=currency),
                raw,
            )
            for raw in self._client.get_transactions(account_id)
        ]

    def get_holdings(self, account_id: str) -> list[InvestmentHolding]:
        return []  # nothing to scrape
