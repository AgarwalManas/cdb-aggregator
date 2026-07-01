# OldBank — screen-scraping mock (Item 6, stretch)

A mock online-banking **website** with no API at all: a login form and an HTML
statement page. It exists to be *scraped*, so the project can dramatize the "old
way" (credential sharing + fragile HTML parsing) against the token-based FDX
"new way".

This directly echoes the pain Wealthsimple has publicly documented — its Roundup
feature once averaged ~10 failed bank connections per day on screen-scraping
aggregators (see `docs/research-report.md`).

## Run it

```bash
uvicorn app.providers.scraper_bank.app:app --app-dir backend --port 9003
```

Open <http://127.0.0.1:9003/> for the login form (user `ada`, password
`hunter2`), then sign in to view the HTML statement.

## Endpoints (a website, not an API)

| Method & path | Notes |
|---|---|
| `GET /` | login form |
| `POST /login` | form `username`/`password` → sets an `oldbank_session` cookie |
| `GET /statement` | HTML statement page; requires the cookie |

No JSON, no token, no scope. The whole "auth" story is a session cookie.

## How it's consumed

The scraper adapter in [`app.adapters.scraper_bank`](../../adapters/scraper_bank.py)
logs in with the customer's real credentials, fetches the statement HTML, and
parses it (BeautifulSoup) into the **same canonical model** as the API sources —
behind the same `SourceAdapter` interface.

What scraping costs you, made concrete:

- **Credentials**, not a token — the adapter must be handed the user's real
  username and password.
- **Fragility** — the parser keys off page structure (`p.balance`, `table.txns`);
  restyle the site and it breaks. There's a test that renames a class and watches
  scraping fail.
- **Scarcity** — no stable transaction ids (synthesized), no pending flag
  (everything reads posted), no holdings, only a display name for the customer.

The structured contrast lives in [`app.comparison`](../../comparison.py)
(`render_comparison()` prints it as a Markdown table).
