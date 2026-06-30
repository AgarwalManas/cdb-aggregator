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

A mock **client-credentials** grant (machine-to-machine: the aggregator
authenticating to the bank). A production FDX integration would use the
authorization-code grant with PKCE under a FAPI profile and a user-consent step;
that user-facing consent is modeled separately in this project's consent layer
(Items 7–8).

| | |
|---|---|
| Token endpoint | `POST /oauth2/token` |
| Grant type | `client_credentials` |
| Client ID | `cdb-aggregator` |
| Client secret | `local-mock-secret` *(mock value, not a real credential)* |
| Scopes | `accounts:read`, `transactions:read`, `customer:read` |

Requesting no `scope` grants all supported scopes. Tokens expire in 1 hour.

```bash
curl -s -X POST http://127.0.0.1:9001/oauth2/token \
  -d grant_type=client_credentials \
  -d client_id=cdb-aggregator -d client_secret=local-mock-secret \
  -d scope="accounts:read transactions:read"
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
