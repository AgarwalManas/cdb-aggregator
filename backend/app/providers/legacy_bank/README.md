# Legacy Bank — messy schema (Item 4)

A second mock source that looks **nothing like FDX**. It's a stand-in for a
legacy core-banking system — the kind of thing you'd otherwise screen-scrape. It
exists for exactly one reason: to give the normalizer (Item 5) something hard to
map. Where the [mock FDX bank](../mock_fdx_bank/README.md) is clean and
standards-native, this one is deliberately awkward.

## Run it

```bash
uvicorn app.providers.legacy_bank.app:app --app-dir backend --port 9002
```

Interactive docs at <http://127.0.0.1:9002/docs>.

## Auth (session, not OAuth2)

```bash
SID=$(curl -s -X POST http://127.0.0.1:9002/api/login \
  -H 'Content-Type: application/json' \
  -d '{"user":"ada","pass":"hunter2"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['sid'])")

curl -s -H "X-Session-Id: $SID" http://127.0.0.1:9002/api/accounts
```

`POST /api/login` returns an opaque `sid` (1-hour TTL). Protected endpoints
require an `X-Session-Id` header. **There are no scopes** — access is
all-or-nothing, which is itself the point: the aggregator's consent layer
(Items 7–8) has to impose the fine-grained control this upstream never offered.

## Endpoints

| Method & path | Auth | Returns |
|---|---|---|
| `POST /api/login` | — | `{ "sid", "ttlSeconds" }` |
| `GET /api/profile` | session | messy customer profile |
| `GET /api/accounts` | session | **one nested blob**: accounts + balances + txns + positions |

## How it differs from FDX (what the adapter must tame)

| Aspect | Legacy bank | (vs FDX bank) |
|---|---|---|
| Auth | opaque session id, no scopes | OAuth2 bearer + scopes |
| Shape | one nested blob | separate flat endpoints |
| Field names | `acctRef`, `amt`, `narrative`, `positions` | `accountId`, `amount`, `description`, `holdings` |
| Money | strings with commas (`"4,210.55"`) | JSON numbers |
| Txn direction | **signed** amount (negative = debit) | unsigned + `debitCreditMemo` |
| Dates | epoch millis (txns) **and** `DD/MM/YYYY` (balances) | ISO 8601 |
| Currency | bare lowercase (`"cad"`) | object (`{"currencyCode":"CAD"}`) |
| Account type | `chequing` / `save` / `tfsa` | `CHECKING` / `SAVINGS` / `BROKERAGE` |
| Status | `active` / `dormant` / `closed` | `OPEN` / `CLOSED` / … |
| Pending | `cleared: false` | `status: "PENDING"` |
| Customer | single `fullName` + one-line `addr` | structured name + address |

The seed data (`data.py`) describes the *same* underlying customer and accounts
as the FDX bank, so Item 5 can normalize both and Item 10 can merge them.
