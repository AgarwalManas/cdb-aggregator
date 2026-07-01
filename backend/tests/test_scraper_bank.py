"""Tests for the screen-scraping mock + scraper adapter + comparison (Item 6).

Covers the credential-login website, the scraper mapping HTML into the *same*
canonical model as the API sources, the fragility that makes scraping a liability
(a layout change breaks it), and the structured old-way/new-way contrast.
"""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from app.adapters import HtmlStatementClient, ScraperBankAdapter
from app.adapters.base import NormalizationError, SourceAdapter
from app.adapters.scraper_bank import parse_accounts
from app.comparison import COMPARISON, render_comparison
from app.models import AccountType, DebitCreditMemo, TransactionStatus
from app.providers.scraper_bank import data as scraper_data
from app.providers.scraper_bank.app import create_app
from app.providers.scraper_bank.auth import OLDBANK_PASS, OLDBANK_USER


def _adapter(
    http: TestClient, user: str = OLDBANK_USER, pw: str = OLDBANK_PASS
) -> ScraperBankAdapter:
    return ScraperBankAdapter(HtmlStatementClient(http, user, pw))


# --- The mock website --------------------------------------------------------


def test_login_form_served() -> None:
    resp = TestClient(create_app()).get("/")
    assert resp.status_code == 200
    assert "<form" in resp.text


def test_statement_requires_session() -> None:
    # No cookie -> 401.
    assert TestClient(create_app()).get("/statement").status_code == 401


def test_login_sets_cookie_and_unlocks_statement() -> None:
    client = TestClient(create_app())
    bad = client.post("/login", data={"username": OLDBANK_USER, "password": "nope"})
    assert bad.status_code == 401

    ok = client.post("/login", data={"username": OLDBANK_USER, "password": OLDBANK_PASS})
    assert ok.status_code == 200
    # The TestClient now holds the session cookie.
    statement = client.get("/statement")
    assert statement.status_code == 200
    assert "OldBank Online Statement" in statement.text


# --- The scraper adapter (same canonical interface) --------------------------


def test_scraper_is_a_source_adapter() -> None:
    adapter = _adapter(TestClient(create_app()))
    assert isinstance(adapter, SourceAdapter)


def test_scraper_end_to_end_snapshot() -> None:
    snap = _adapter(TestClient(create_app())).snapshot()
    assert snap.source == "scraper_bank"
    assert snap.customer.name.full == "Ada Lovelace"

    accounts = {a.account_id: a for a in snap.accounts}
    assert set(accounts) == {"****1234", "****5678"}  # masked numbers are the ids
    chequing = accounts["****1234"]
    assert chequing.account_type is AccountType.CHECKING
    assert chequing.currency == "CAD"
    assert chequing.balances[0].current == Decimal("4210.55")  # "$4,210.55" parsed


def test_scraper_transactions_and_scarcity() -> None:
    adapter = _adapter(TestClient(create_app()))
    txns = {t.transaction_id: t for t in adapter.get_transactions("****1234")}
    # Ids are synthesized (statements have none).
    assert set(txns) == {"****1234-0", "****1234-1"}
    debit = txns["****1234-0"]  # "-$85.20"
    assert debit.amount == Decimal("85.20")
    assert debit.debit_credit_memo is DebitCreditMemo.DEBIT
    assert txns["****1234-1"].debit_credit_memo is DebitCreditMemo.CREDIT  # "$2,400.00"
    # A statement can't tell you what's pending — everything reads posted.
    assert all(t.status is TransactionStatus.POSTED for t in txns.values())
    # And there are no holdings to scrape.
    assert adapter.get_holdings("****1234") == []


# --- Fragility: the whole point of the contrast ------------------------------


def test_scraping_breaks_when_layout_changes() -> None:
    good_html = scraper_data.render_statement_html()
    assert parse_accounts(good_html)  # works on the expected layout

    # Bank restyles: the balance paragraph's class is renamed.
    broken = good_html.replace('class="balance"', 'class="bal"')
    with pytest.raises(ValueError, match="layout changed|missing heading/balance"):
        parse_accounts(broken)


def test_scraper_wrong_credentials_fail() -> None:
    adapter = _adapter(TestClient(create_app()), pw="wrong-password")
    # Credential dependency: bad password -> login 401 -> the scrape can't proceed.
    with pytest.raises(httpx.HTTPStatusError):
        adapter.get_customer()


def test_unrecognized_account_surfaces_normalization_error() -> None:
    holdings_page = scraper_data.render_statement_html(
        accounts=[
            {
                "name": "Crypto Wallet",  # a name the mapper doesn't know
                "masked": "****9999",
                "balance": "1,000.00",
                "currency": "CAD",
                "txns": [],
            }
        ]
    )

    class FixedClient(HtmlStatementClient):
        def _statement(self) -> str:
            return holdings_page

    adapter = ScraperBankAdapter(FixedClient(TestClient(create_app()), "u", "p"))
    with pytest.raises(NormalizationError) as exc:
        adapter.get_accounts()
    assert exc.value.source == "scraper_bank"
    assert exc.value.entity == "account"


# --- Old way vs new way ------------------------------------------------------


def test_comparison_covers_key_dimensions() -> None:
    dimensions = {c.dimension for c in COMPARISON}
    assert {"Authentication", "Consent & revocation", "Stability"} <= dimensions
    # The credential-sharing pain and the token answer both appear.
    auth = next(c for c in COMPARISON if c.dimension == "Authentication")
    assert "password" in auth.screen_scraping.lower()
    assert "token" in auth.fdx_open_banking.lower()


def test_render_comparison_is_markdown_table() -> None:
    table = render_comparison()
    assert table.startswith("| Dimension |")
    assert "OAuth2" in table
