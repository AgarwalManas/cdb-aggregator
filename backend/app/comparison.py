"""Old way vs new way: screen-scraping vs token-based FDX access.

A small, structured contrast between the two ways an aggregator can get at a
customer's bank data. It's deliberately code (not just prose) so it can be
asserted in tests and rendered wherever it's useful — and because the whole
project is an argument for the right-hand column.

The framing reflects a well-documented problem: scraping-based aggregators have
reported on the order of ten failed bank connections a day, and open-banking
advocacy is largely about replacing exactly this. See ``docs/research-report.md``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApproachContrast:
    """One dimension on which the two approaches differ."""

    dimension: str
    screen_scraping: str
    fdx_open_banking: str


#: The contrast, dimension by dimension. Left = what the scraper adapter (Item 6)
#: is forced to do; right = what the FDX bank + consent layer provide.
COMPARISON: tuple[ApproachContrast, ...] = (
    ApproachContrast(
        dimension="Authentication",
        screen_scraping="User hands over their real banking username & password",
        fdx_open_banking="OAuth2 token; credentials never leave the bank",
    ),
    ApproachContrast(
        dimension="Granularity",
        screen_scraping="All-or-nothing: whoever holds the login sees everything",
        fdx_open_banking="Granular scopes (accounts / transactions / holdings) per grant",
    ),
    ApproachContrast(
        dimension="Consent & revocation",
        screen_scraping="No consent record; 'revoke' means changing your password",
        fdx_open_banking="Explicit, time-limited, revocable consent with an audit trail",
    ),
    ApproachContrast(
        dimension="Data quality",
        screen_scraping="Whatever the HTML shows: no stable ids, no pending flag, no holdings",
        fdx_open_banking="Structured, typed resources with stable ids",
    ),
    ApproachContrast(
        dimension="Stability",
        screen_scraping="Breaks silently when the bank restyles its site",
        fdx_open_banking="Versioned API contract",
    ),
    ApproachContrast(
        dimension="Traceability",
        screen_scraping="Indistinguishable from the user logging in; invisible to the bank",
        fdx_open_banking="Attributable, logged, standardized access",
    ),
)


def render_comparison() -> str:
    """Render :data:`COMPARISON` as a Markdown table."""
    lines = [
        "| Dimension | Screen-scraping (old way) | FDX open banking (new way) |",
        "|---|---|---|",
    ]
    lines += [f"| {c.dimension} | {c.screen_scraping} | {c.fdx_open_banking} |" for c in COMPARISON]
    return "\n".join(lines)
