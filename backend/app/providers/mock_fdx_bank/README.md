# Mock FDX Bank (Item 3)

A small, standalone mock **FDX data provider**. It issues OAuth2 access tokens
and serves **FDX-shaped JSON** from Bearer-protected resource endpoints. This is
the project's *clean, standards-native* source — the easy case for the
normalizer (Item 5), in deliberate contrast to the messy source built in Item 4.

It is intentionally **decoupled** from the aggregator's canonical model
(`app.models`): a real bank doesn't import our types. The Item 5 adapter is what
maps this provider's FDX JSON into the canonical model.

## Run it

```bash
uvicorn app.providers.mock_fdx_bank.app:app --app-dir backend --port 9001
```

Interactive docs at <http://127.0.0.1:9001/docs>.

## OAuth2

Two grants are supported:

- **`authorization_code` + PKCE, initiated via PAR** (item-23) — the FAPI-shaped
  flow the adapter uses. See *FAPI coverage* below.
- **`client_credentials`** — a machine-to-machine convenience, kept so the token
  endpoint is trivially callable with `curl`.

| | |
|---|---|
| PAR endpoint | `POST /oauth2/par` |
| Authorization endpoint | `GET /oauth2/authorize` |
| Token endpoint | `POST /oauth2/token` |
| Client ID | `cdb-aggregator` |
| Client secret | `local-mock-secret` *(mock value, not a real credential)* |
| Scopes | `accounts:read`, `transactions:read`, `customer:read` |

Requesting no `scope` grants all supported scopes. Tokens expire in 1 hour.

```bash
# Quick machine-to-machine token:
curl -s -X POST http://127.0.0.1:9001/oauth2/token \
  -d grant_type=client_credentials \
  -d client_id=cdb-aggregator -d client_secret=local-mock-secret \
  -d scope="accounts:read transactions:read"
```

### FAPI coverage

FDX mandates the **FAPI** security profile. This mock models the security-critical
parts of that flow so the adapter exercises them rather than a toy token call:

**Covered**

- **PKCE (RFC 7636), `S256` only** — the client sends a `code_challenge` at PAR
  time and proves the matching `code_verifier` when redeeming the code; a mismatch
  is rejected as `invalid_grant`. `plain` is refused.
- **Pushed Authorization Requests (RFC 9126)** — the request is pushed to
  `/oauth2/par`, which returns a short-lived, single-use `request_uri`; the
  authorization endpoint accepts *only* a pushed `request_uri`.
- **Single-use, short-lived artifacts** — `request_uri` (90 s) and authorization
  code (60 s) are each consumed on first use.
- **Confidential-client authentication** on every token/PAR call.

**Out of scope (documented, not implemented)**

- **Sender-constrained tokens** (mTLS or DPoP) — FAPI requires binding the token
  to the client's key. The mock issues bearer tokens; this is the main remaining
  FAPI gap and is noted in the threat model.
- **Signed request objects / JARM**, browser redirect + real user authentication
  (the mock's `/authorize` returns the code as JSON since there is no user agent),
  and a discovery document.

```bash
# FAPI flow (PAR -> authorize -> token) is what the adapter drives; see
# app/adapters/fdx_bank.py::FdxHttpClient._fetch_token.
```

## Resource endpoints

All require `Authorization: Bearer <token>` and the noted scope. Base path is
`/fdx/v6`.

| Method & path | Scope | Returns |
|---|---|---|
| `GET /fdx/v6/customers/current` | `customer:read` | the authenticated customer |
| `GET /fdx/v6/accounts` | `accounts:read` | account summaries (no holdings) |
| `GET /fdx/v6/accounts/{id}` | `accounts:read` | account detail: balances; holdings if investment |
| `GET /fdx/v6/accounts/{id}/transactions` | `transactions:read` | the account's transactions |

Auth failures follow OAuth2/RFC 6750: `401` with a `WWW-Authenticate` header for
a missing/invalid/expired token, `403` (`insufficient_scope`) when the token is
valid but lacks a required scope.

## FDX shape notes

Worth knowing when writing the adapter (Item 5):

- **Currency is an object**: `"currency": {"currencyCode": "CAD"}`, not a bare
  string.
- **Balances are fields on the account** (`currentBalance`, `availableBalance`,
  `balanceType`, `balanceAsOf`).
- **Transactions** use FDX's unsigned-`amount` + `debitCreditMemo` convention; a
  pending transaction has no `postedTimestamp`.
- **Holdings** use `units` (not "quantity") and embed in the investment account
  detail.

Seed data lives in `data.py` (one customer; chequing, savings, and a
self-directed investment account with holdings).
