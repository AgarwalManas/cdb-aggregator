"""Seed data + HTML rendering for the screen-scraping mock (Item 6).

This source has no API at all — just an online-banking **web page** a user would
log into. The aggregator has to scrape it. ``render_statement_html`` builds the
statement page from the same underlying facts as the other banks, so the
scraper's output can be compared apples-to-apples.

The HTML layout is exactly the kind of thing that quietly changes when a bank
redesigns its site — which is what makes scraping fragile (see the parser and
the fragility test).
"""

from __future__ import annotations

from typing import Any

HOLDER_NAME = "Ada Lovelace"
STATEMENT_DATE = "2026-06-30"  # the only "as of" a statement gives you

#: Accounts as they'd appear on a statement page: a display name, a masked
#: number, a formatted balance, and (maybe) a transactions table. No stable ids,
#: no pending flag, no holdings — that scarcity is part of the story.
ACCOUNTS: list[dict[str, Any]] = [
    {
        "name": "Chequing",
        "masked": "****1234",
        "balance": "4,210.55",
        "currency": "CAD",
        "txns": [
            {"date": "2026-06-27", "desc": "LOBLAWS #1234", "amount": "-85.20"},
            {"date": "2026-06-26", "desc": "PAYROLL DEPOSIT", "amount": "2,400.00"},
        ],
    },
    {
        "name": "Savings",
        "masked": "****5678",
        "balance": "15,800.00",
        "currency": "CAD",
        "txns": [],
    },
]


def _fmt_amount(amount: str) -> str:
    """'-85.20' -> '-$85.20'; '2,400.00' -> '$2,400.00' (statement styling)."""
    if amount.startswith("-"):
        return f"-${amount[1:]}"
    return f"${amount}"


def _txn_row(txn: dict[str, Any]) -> str:
    return (
        f'<tr><td class="date">{txn["date"]}</td>'
        f'<td class="desc">{txn["desc"]}</td>'
        f'<td class="amt">{_fmt_amount(txn["amount"])}</td></tr>'
    )


def _account_section(account: dict[str, Any]) -> str:
    rows = "".join(_txn_row(t) for t in account["txns"])
    table = (
        '<table class="txns"><tr><th>Date</th><th>Description</th><th>Amount</th></tr>'
        f"{rows}</table>"
        if account["txns"]
        else ""
    )
    return (
        f'<div class="account" data-acct="{account["masked"]}">'
        f"<h2>{account['name']} ({account['masked']})</h2>"
        f'<p class="balance">Balance: ${account["balance"]} {account["currency"]}</p>'
        f"{table}</div>"
    )


def render_statement_html(
    accounts: list[dict[str, Any]] | None = None,
    holder: str = HOLDER_NAME,
    as_of: str = STATEMENT_DATE,
) -> str:
    """Render the online-banking statement page the scraper will parse."""
    sections = "".join(
        _account_section(a) for a in (accounts if accounts is not None else ACCOUNTS)
    )
    return (
        "<html><body>"
        "<h1>OldBank Online Statement</h1>"
        f'<p class="acct-holder">Account holder: {holder}</p>'
        f'<p class="statement-date">As of: {as_of}</p>'
        f"{sections}"
        "</body></html>"
    )


LOGIN_FORM_HTML = (
    "<html><body><h1>OldBank Login</h1>"
    '<form method="post" action="/login">'
    '<input name="username" placeholder="Username"/>'
    '<input name="password" type="password" placeholder="Password"/>'
    '<button type="submit">Sign in</button>'
    "</form></body></html>"
)
