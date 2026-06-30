"""Tests for the legacy (messy-schema) bank (Item 4).

Two jobs: confirm the session-auth flow and the deliberately-messy payload shape,
then prove the mess is *tractable* — a focused normalization maps one legacy
account, balance, transaction, and holding into the canonical model (Item 2).
That tractability check is what de-risks the Item 5 adapter.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models import (
    Account,
    AccountCategory,
    AccountType,
    Balance,
    DebitCreditMemo,
    InvestmentHolding,
    Transaction,
    TransactionStatus,
)
from app.providers.legacy_bank.app import create_app
from app.providers.legacy_bank.auth import LEGACY_PASS, LEGACY_USER


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _session(client: TestClient) -> str:
    resp = client.post("/api/login", json={"user": LEGACY_USER, "pass": LEGACY_PASS})
    assert resp.status_code == 200, resp.text
    return resp.json()["sid"]


def _hdr(sid: str) -> dict[str, str]:
    return {"X-Session-Id": sid}


# --- Session auth ------------------------------------------------------------


def test_login_returns_session(client: TestClient) -> None:
    resp = client.post("/api/login", json={"user": LEGACY_USER, "pass": LEGACY_PASS})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sid"]
    assert body["ttlSeconds"] > 0


def test_login_rejects_bad_credentials(client: TestClient) -> None:
    resp = client.post("/api/login", json={"user": LEGACY_USER, "pass": "nope"})
    assert resp.status_code == 401


def test_protected_requires_session(client: TestClient) -> None:
    assert client.get("/api/accounts").status_code == 401
    assert client.get("/api/accounts", headers=_hdr("garbage")).status_code == 401


# --- Messy shape -------------------------------------------------------------


def test_accounts_is_one_nested_blob(client: TestClient) -> None:
    blob = client.get("/api/accounts", headers=_hdr(_session(client))).json()
    assert blob["custId"] == "GBC-771"
    refs = {a["acctRef"] for a in blob["accounts"]}
    assert refs == {"GB-CHQ-9981", "GB-SAV-3310", "GB-INV-2207"}

    chq = next(a for a in blob["accounts"] if a["acctRef"] == "GB-CHQ-9981")
    # Messy markers: bare lowercase currency, nested comma-string balance,
    # DD/MM/YYYY date, embedded transactions with signed amounts + epoch millis.
    assert chq["ccy"] == "cad"
    assert chq["balance"]["ledger"] == "4,210.55"
    assert chq["asOf"] == "29/06/2026"
    out_txn = next(t for t in chq["txns"] if t["id"] == "T-5501")
    assert out_txn["amt"] < 0  # signed: negative == debit
    assert isinstance(out_txn["when"], int)  # epoch millis, not ISO
    assert out_txn["cleared"] is True


def test_investment_uses_positions_not_holdings(client: TestClient) -> None:
    blob = client.get("/api/accounts", headers=_hdr(_session(client))).json()
    inv = next(a for a in blob["accounts"] if a["acctRef"] == "GB-INV-2207")
    assert "positions" in inv and "holdings" not in inv
    assert {p["sym"] for p in inv["positions"]} == {"VFV", "SHOP", None}


def test_profile_is_unstructured(client: TestClient) -> None:
    profile = client.get("/api/profile", headers=_hdr(_session(client))).json()
    assert profile["fullName"] == "Ada Lovelace"  # single string, not first/last
    assert "," in profile["contact"]["addr"]  # one-line address


# --- Tractability: the mess maps into the canonical model --------------------

# Minimal mappers — the kind of logic the Item 5 adapter will formalize.
_KIND_TO_TYPE = {
    "chequing": (AccountCategory.DEPOSIT_ACCOUNT, AccountType.CHECKING),
    "save": (AccountCategory.DEPOSIT_ACCOUNT, AccountType.SAVINGS),
    "tfsa": (AccountCategory.INVESTMENT_ACCOUNT, AccountType.TFSA),
}


def _money(s: str) -> Decimal:
    """'4,210.55' -> Decimal('4210.55')."""
    return Decimal(s.replace(",", ""))


def test_legacy_account_can_be_normalized(client: TestClient) -> None:
    blob = client.get("/api/accounts", headers=_hdr(_session(client))).json()
    chq = next(a for a in blob["accounts"] if a["acctRef"] == "GB-CHQ-9981")

    category, acct_type = _KIND_TO_TYPE[chq["kind"]]
    as_of = datetime.strptime(chq["asOf"], "%d/%m/%Y").replace(tzinfo=UTC)
    account = Account(
        account_id=chq["acctRef"],
        category=category,
        account_type=acct_type,
        status="OPEN" if chq["openState"] == "active" else "CLOSED",
        currency=chq["ccy"].upper(),  # "cad" -> "CAD"
        nickname=chq["label"],
        balances=[
            Balance(
                as_of=as_of,
                currency=chq["ccy"].upper(),
                current=_money(chq["balance"]["ledger"]),
                available=_money(chq["balance"]["available"]),
            )
        ],
    )
    assert account.account_type is AccountType.CHECKING
    assert account.balances[0].current == Decimal("4210.55")

    # A signed, epoch-stamped transaction -> canonical unsigned + memo + status.
    raw = next(t for t in chq["txns"] if t["id"] == "T-5503")  # the un-cleared one
    txn = Transaction(
        transaction_id=raw["id"],
        account_id=chq["acctRef"],
        amount=abs(Decimal(str(raw["amt"]))),
        currency=chq["ccy"].upper(),
        debit_credit_memo=DebitCreditMemo.DEBIT if raw["amt"] < 0 else DebitCreditMemo.CREDIT,
        status=TransactionStatus.POSTED if raw["cleared"] else TransactionStatus.PENDING,
        transaction_timestamp=datetime.fromtimestamp(raw["when"] / 1000, tz=UTC),
        posted_timestamp=(
            datetime.fromtimestamp(raw["when"] / 1000, tz=UTC) if raw["cleared"] else None
        ),
        description=raw["narrative"],
    )
    assert txn.amount == Decimal("42.99")
    assert txn.debit_credit_memo is DebitCreditMemo.DEBIT
    assert txn.status is TransactionStatus.PENDING


def test_legacy_position_can_be_normalized(client: TestClient) -> None:
    blob = client.get("/api/accounts", headers=_hdr(_session(client))).json()
    inv = next(a for a in blob["accounts"] if a["acctRef"] == "GB-INV-2207")
    pos = next(p for p in inv["positions"] if p["sym"] == "VFV")

    holding = InvestmentHolding(
        holding_id=f"{inv['acctRef']}:{pos['sym']}",
        account_id=inv["acctRef"],
        holding_type="ETF" if pos["assetClass"] == "etf" else "OTHER",
        symbol=pos["sym"],
        quantity=Decimal(str(pos["qty"])),
        cost_basis=_money(pos["book"]),
        current_unit_price=_money(pos["last"]),
        market_value=_money(pos["mktVal"]),
        currency=inv["ccy"].upper(),
        as_of=datetime.strptime(inv["asOf"], "%d/%m/%Y").replace(tzinfo=UTC),
    )
    assert holding.market_value == Decimal("5512.50")
