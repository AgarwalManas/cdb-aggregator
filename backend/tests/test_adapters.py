"""Per-adapter tests for the normalizer layer (Item 5).

Three tiers:

1. **Unit / mapping** — fake clients return the providers' own seed data; the
   adapters must produce correct canonical models. This is where schema drift is
   pinned down (comma money, signed amounts, epoch dates, vocab, FDX currency
   objects). No network.
2. **Error handling** — a malformed raw record surfaces as a
   ``NormalizationError`` with source/entity/id context.
3. **Integration** — the real HTTP clients run against the actual provider apps
   in-process (via Starlette's TestClient), exercising auth + transport + mapping
   end-to-end.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.adapters import (
    FdxBankAdapter,
    FdxHttpClient,
    LegacyBankAdapter,
    LegacyHttpClient,
    NormalizationError,
)
from app.models import (
    AccountCategory,
    AccountType,
    DebitCreditMemo,
    TransactionStatus,
)
from app.providers.legacy_bank import data as legacy_data
from app.providers.legacy_bank.app import create_app as create_legacy_app
from app.providers.legacy_bank.auth import LEGACY_PASS, LEGACY_USER
from app.providers.mock_fdx_bank import data as fdx_data
from app.providers.mock_fdx_bank.app import create_app as create_fdx_app
from app.providers.mock_fdx_bank.auth import CLIENT_ID, CLIENT_SECRET

# --- Fake transport clients backed by the providers' seed data ---------------


class FakeFdxClient:
    def get_customer(self) -> dict[str, Any]:
        return fdx_data.CUSTOMER

    def get_accounts(self) -> list[dict[str, Any]]:
        return [fdx_data.account_summary(a) for a in fdx_data.ACCOUNTS.values()]

    def get_account(self, account_id: str) -> dict[str, Any]:
        return fdx_data.ACCOUNTS[account_id]

    def get_transactions(self, account_id: str) -> list[dict[str, Any]]:
        return fdx_data.TRANSACTIONS.get(account_id, [])

    def get_holdings(self, account_id: str) -> list[dict[str, Any]]:
        return fdx_data.ACCOUNTS[account_id].get("holdings", [])


class FakeLegacyClient:
    def _account(self, account_id: str) -> dict[str, Any]:
        return next(a for a in legacy_data.ACCOUNTS if a["acctRef"] == account_id)

    def get_customer(self) -> dict[str, Any]:
        return legacy_data.PROFILE

    def get_accounts(self) -> list[dict[str, Any]]:
        return legacy_data.ACCOUNTS

    def get_account(self, account_id: str) -> dict[str, Any]:
        return self._account(account_id)

    def get_transactions(self, account_id: str) -> list[dict[str, Any]]:
        return self._account(account_id).get("txns", [])

    def get_holdings(self, account_id: str) -> list[dict[str, Any]]:
        return self._account(account_id).get("positions", [])


# --- FDX adapter: mapping ----------------------------------------------------


def test_fdx_adapter_customer() -> None:
    customer = FdxBankAdapter(FakeFdxClient()).get_customer()
    assert customer.customer_id == "cust-001"
    assert customer.name.full == "Ada Lovelace"
    assert customer.emails == ["ada@example.com"]
    assert customer.addresses[0].country == "CA"


def test_fdx_adapter_accounts_unwrap_currency_object() -> None:
    accounts = {a.account_id: a for a in FdxBankAdapter(FakeFdxClient()).get_accounts()}
    chq = accounts["acc-chq-001"]
    assert chq.account_type is AccountType.CHECKING
    assert chq.currency == "CAD"  # unwrapped from {"currencyCode": "CAD"}
    assert chq.customer_id == "cust-001"  # FDX carries it
    assert chq.balances[0].current == Decimal("4210.55")
    assert chq.balances[0].available == Decimal("4100.00")


def test_fdx_adapter_transactions_thread_account_currency() -> None:
    txns = {
        t.transaction_id: t for t in FdxBankAdapter(FakeFdxClient()).get_transactions("acc-chq-001")
    }
    # FDX txns carry no currency; the adapter threads the account's.
    assert txns["txn-1001"].currency == "CAD"
    assert txns["txn-1001"].debit_credit_memo is DebitCreditMemo.DEBIT
    assert txns["txn-1001"].amount == Decimal("85.20")
    assert txns["txn-1003"].status is TransactionStatus.PENDING
    assert txns["txn-1003"].posted_timestamp is None


def test_fdx_adapter_holdings_units_to_quantity() -> None:
    holdings = {h.symbol: h for h in FdxBankAdapter(FakeFdxClient()).get_holdings("acc-inv-001")}
    assert holdings["VFV"].quantity == Decimal("50")  # from "units"
    assert holdings["VFV"].market_value == Decimal("5512.50")


# --- Legacy adapter: mapping (the hard one) ----------------------------------


def test_legacy_adapter_translates_vocab_and_currency() -> None:
    accounts = {a.account_id: a for a in LegacyBankAdapter(FakeLegacyClient()).get_accounts()}
    chq = accounts["GB-CHQ-9981"]
    assert chq.category is AccountCategory.DEPOSIT_ACCOUNT
    assert chq.account_type is AccountType.CHECKING  # "chequing" -> CHECKING
    assert chq.currency == "CAD"  # "cad" -> "CAD"
    assert chq.customer_id is None  # legacy accounts don't carry it
    # Comma-string, nested balance parsed to Decimal.
    assert chq.balances[0].current == Decimal("4210.55")
    tfsa = accounts["GB-INV-2207"]
    assert tfsa.account_type is AccountType.TFSA
    assert tfsa.category is AccountCategory.INVESTMENT_ACCOUNT


def test_legacy_adapter_signed_amount_becomes_memo() -> None:
    txns = {
        t.transaction_id: t
        for t in LegacyBankAdapter(FakeLegacyClient()).get_transactions("GB-CHQ-9981")
    }
    out = txns["T-5501"]  # amt: -85.20
    assert out.amount == Decimal("85.20")  # unsigned
    assert out.debit_credit_memo is DebitCreditMemo.DEBIT  # sign -> direction
    assert out.currency == "CAD"  # threaded from account
    inflow = txns["T-5502"]  # amt: +2400
    assert inflow.debit_credit_memo is DebitCreditMemo.CREDIT
    pending = txns["T-5503"]  # cleared: false
    assert pending.status is TransactionStatus.PENDING
    assert pending.posted_timestamp is None
    # epoch millis -> aware datetime
    assert out.transaction_timestamp.tzinfo is not None


def test_legacy_adapter_positions_to_holdings() -> None:
    holdings = {
        h.symbol: h for h in LegacyBankAdapter(FakeLegacyClient()).get_holdings("GB-INV-2207")
    }
    assert holdings["VFV"].market_value == Decimal("5512.50")  # "5,512.50" parsed
    assert holdings["VFV"].quantity == Decimal("50")
    assert holdings[None].holding_type.value == "CASH"  # the cash position
    # as_of borrowed from the account's DD/MM/YYYY date
    assert holdings["VFV"].as_of.year == 2026


def test_legacy_customer_splits_name_and_parses_address() -> None:
    customer = LegacyBankAdapter(FakeLegacyClient()).get_customer()
    assert customer.name.first == "Ada"
    assert customer.name.last == "Lovelace"
    assert customer.addresses[0].city == "Toronto"
    assert customer.addresses[0].postal_code == "M5V 1A1"
    assert customer.addresses[0].country == "CA"


# --- Snapshot (common interface) ---------------------------------------------


def test_snapshot_pulls_holdings_only_for_investment_accounts() -> None:
    snap = LegacyBankAdapter(FakeLegacyClient()).snapshot()
    assert snap.source == "legacy_bank"
    assert len(snap.accounts) == 3
    # Every account has transactions; only the investment account has holdings.
    assert set(snap.transactions) == {"GB-CHQ-9981", "GB-SAV-3310", "GB-INV-2207"}
    assert set(snap.holdings) == {"GB-INV-2207"}


def test_both_sources_normalize_to_the_same_shape() -> None:
    """Different inputs, one canonical output — the reason this layer exists."""
    fdx = FdxBankAdapter(FakeFdxClient()).snapshot()
    legacy = LegacyBankAdapter(FakeLegacyClient()).snapshot()
    for snap in (fdx, legacy):
        chequing = next(a for a in snap.accounts if a.account_type is AccountType.CHECKING)
        assert chequing.currency == "CAD"
        assert chequing.balances[0].current == Decimal("4210.55")


# --- Error handling ----------------------------------------------------------


def test_bad_record_raises_normalization_error() -> None:
    class BrokenFdxClient(FakeFdxClient):
        def get_accounts(self) -> list[dict[str, Any]]:
            # Missing the required "currency" object.
            return [
                {"accountId": "x", "accountCategory": "DEPOSIT_ACCOUNT", "accountType": "CHECKING"}
            ]

    with pytest.raises(NormalizationError) as exc_info:
        FdxBankAdapter(BrokenFdxClient()).get_accounts()
    err = exc_info.value
    assert err.source == "mock_fdx_bank"
    assert err.entity == "account"
    assert err.identifier == "x"


# --- Integration: real HTTP clients against the running provider apps ---------


def test_fdx_integration_end_to_end() -> None:
    http = TestClient(create_fdx_app())  # in-process ASGI transport
    adapter = FdxBankAdapter(FdxHttpClient(http, CLIENT_ID, CLIENT_SECRET))
    snap = adapter.snapshot()
    assert snap.customer.customer_id == "cust-001"
    assert {a.account_id for a in snap.accounts} == {"acc-chq-001", "acc-sav-001", "acc-inv-001"}
    assert snap.holdings["acc-inv-001"]  # holdings fetched for the investment account


def test_legacy_integration_end_to_end() -> None:
    http = TestClient(create_legacy_app())
    adapter = LegacyBankAdapter(LegacyHttpClient(http, LEGACY_USER, LEGACY_PASS))
    snap = adapter.snapshot()
    assert snap.customer.name.full == "Ada Lovelace"
    chequing = next(a for a in snap.accounts if a.account_type is AccountType.CHECKING)
    assert chequing.balances[0].current == Decimal("4210.55")
    assert snap.transactions["GB-CHQ-9981"]
