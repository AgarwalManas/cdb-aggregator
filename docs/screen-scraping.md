# Why screen-scraping is about to break

Most account aggregation in Canada still works the old way: you give a third-party
app your **real banking username and password**, and it logs in *as you* and
scrapes the HTML of your account pages. Consumer-Driven Banking is about to make
that both unnecessary and untenable. This is the argument for building FDX-first —
and this repo is a working demonstration of both sides.

## How the old way works

1. You hand over your bank credentials to an aggregator (directly, or via a
   connectivity provider).
2. The aggregator logs into your online banking as you and **parses the HTML** of
   your statement pages to extract accounts, balances, and transactions.

Two structural problems fall out of this:

- **Credentials, not tokens.** The aggregator holds the keys to your entire bank
  login — all accounts, all actions — with no notion of scope, expiry, or a
  revocation that isn't "change your password." There is no consent record and no
  way for the bank to tell your access apart from you logging in yourself.
- **Fragility.** A scraper depends on the *structure* of a web page. When the bank
  restyles its site — renames a CSS class, reorders a column — the scraper
  silently breaks. There is no contract, so there is no stability.

Wealthsimple documented this pain concretely: its Roundup feature once averaged
**~10 failed bank connections per day** on screen-scraping aggregators, and its
2019 open-banking submission cited exactly this brittleness. The industry still
leans on credential-based connectivity (Flinks, Plaid, and in-house tools) to
paper over it. (Sources: this project's [`docs/research-report.md`](research-report.md).)

## Why it's about to break

Canada's regulatory ground has shifted:

- **Bill C-15 received Royal Assent on March 26, 2026**, repealing the original
  Consumer-Driven Banking Act and replacing it with a comprehensive new **CDBA**,
  and moving oversight to the **Bank of Canada** (which already supervises fintechs
  like Wealthsimple under the Retail Payment Activities Act).
- **Phase 1 (read access)** was targeted for early 2026; **Phase 2 (write —
  payment initiation, account switching)** for mid-2027, contingent on Real-Time
  Rail. (As of early 2026 the Bank of Canada had not committed to a firm launch
  date, so timing is genuinely uncertain — build for it, don't claim it.)
- The technical standard is **FDX**: OAuth 2.0 + FAPI security profiles, granular
  and time-limited permissions, and five principles — **Control, Access,
  Transparency, Traceability, Security** — royalty-free to implement.

Under an accredited, consent-based regime, credential sharing stops being the
workaround and becomes the thing the framework exists to replace. Accredited
participants connect through **token-based APIs with explicit, revocable consent**;
screen-scraping becomes both unnecessary and out of step with the rules.

## Old way vs new way

The same contrast, encoded in the repo as `app.comparison`
(`render_comparison()` prints this table):

| Dimension | Screen-scraping (old way) | FDX open banking (new way) |
|---|---|---|
| Authentication | User hands over their real banking username & password | OAuth2 token; credentials never leave the bank |
| Granularity | All-or-nothing: whoever holds the login sees everything | Granular scopes (accounts / transactions / holdings) per grant |
| Consent & revocation | No consent record; "revoke" means changing your password | Explicit, time-limited, revocable consent with an audit trail |
| Data quality | Whatever the HTML shows: no stable ids, no pending flag, no holdings | Structured, typed resources with stable ids |
| Stability | Breaks silently when the bank restyles its site | Versioned API contract |
| Traceability | Indistinguishable from the user logging in; invisible to the bank | Attributable, logged, standardized access |

## See it in this repo

Both sides are runnable, not just described:

- **The old way** — `app.providers.scraper_bank` is a mock bank *website* (login
  form + HTML statement, no API). `app.adapters.scraper_bank` scrapes it into the
  canonical model. Its **fragility is a test**: rename a CSS class and
  `test_scraping_breaks_when_layout_changes` watches the scraper fail — the exact
  failure mode that costs those ~10 connections a day.
- **The new way** — `app.providers.mock_fdx_bank` issues OAuth2 tokens and serves
  FDX-shaped JSON; the consent + traceability engine (Items 7–8) gives it scoped,
  revocable, logged, minimized access.

The point of the contrast isn't that scraping is done badly here — it's that
scraping is *inherently* the wrong shape for a world where the consumer, not the
credential, is in control.
