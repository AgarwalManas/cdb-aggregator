# FDX schema conformance

This project models an **FDX-shaped** data provider. To move that from a claim to
something enforced, the mock FDX bank's responses are validated against JSON
Schemas on every test run — so a change that drifts from the FDX shape **fails the
build** (`backend/tests/test_fdx_conformance.py`).

> **Honest caveat.** FDX's official JSON Schemas are published to FDX members
> under licence and aren't redistributed here. The schemas in
> `backend/app/providers/mock_fdx_bank/fdx_schemas/` are a **hand-authored subset**
> that encodes the FDX field shapes and conventions this project uses (a
> `currency` object, balance fields on the account, the unsigned-`amount` +
> `debitCreditMemo` transaction convention, `units` on holdings). The conformance
> claim is therefore: *the mock provider's responses conform to a documented
> FDX-subset schema, checked automatically*, on the surface below.

## What's validated

The conformance test drives the running provider and validates each real response:

| Entity | Endpoint | Schema |
|---|---|---|
| Customer | `GET /fdx/v6/customers/current` | `customer.schema.json` |
| Account (summary) | `GET /fdx/v6/accounts` | `account.schema.json` |
| Account (detail) + balance fields | `GET /fdx/v6/accounts/{id}` | `account.schema.json` |
| Investment holding | (embedded in account detail) | `holding.schema.json` |
| Transaction | `GET /fdx/v6/accounts/{id}/transactions` | `transaction.schema.json` |

Schemas use `additionalProperties: false`, so drift is caught both ways: a removed
or renamed **required** field fails, and an **unexpected** field fails. Amounts on
transactions are constrained to unsigned (`minimum: 0`), matching FDX's
`debitCreditMemo` direction convention.

## Field coverage

- **Customer** — `customerId`, `name{first,last}` (required); `email`, `addresses[]`
  (`line1`, `city`, `region`, `postalCode`, `country`).
- **Account** — `accountId`, `accountCategory`, `accountType`, `currency{currencyCode}`
  (required); `customerId`, `nickname`, `status`, `maskedAccountNumber`.
- **Balance** — carried on the account: `balanceType` (ASSET/LIABILITY),
  `currentBalance`, `availableBalance`, `balanceAsOf`.
- **Holding** — `holdingId`, `holdingType`, `units`, `currency`, `asOf` (required);
  `symbol` (nullable), `costBasis`, `currentUnitPrice`, `marketValue`.
- **Transaction** — `transactionId`, `accountId`, `amount` (unsigned),
  `debitCreditMemo`, `status`, `transactionTimestamp` (required); `postedTimestamp`
  (absent when pending), `description`, `category`.

## Canonical model ↔ FDX

The canonical model (`app.models`) is **FDX-aligned, not byte-identical** — the
normalizer's whole job is to tame source differences into one internal shape, so
some fields are deliberately renamed. That's why conformance is asserted on the
**provider (FDX) surface**, with the canonical mapping documented here:

| FDX (provider) | Canonical (`app.models`) |
|---|---|
| `currency: {currencyCode}` | `currency: "CAD"` (unwrapped string) |
| `maskedAccountNumber` | `masked_number` |
| balance fields on account | a `Balance` object in `balances[]` |
| `units` (holding) | `quantity` |
| `email` (single) | `emails: []` |
| `amount` + `debitCreditMemo` | unsigned `amount` + `debit_credit_memo` (kept) |

## Out of scope

- FDX pagination envelopes, and the many optional FDX fields the mock doesn't emit.
- Other FDX entities (statements, payments, rewards, etc.).
- The official FDX `$id`/`$ref` schema graph and version negotiation.
- The **legacy** and **scraped** providers — they're deliberately *non*-FDX (that's
  the normalizer's hard case); only the FDX provider is held to FDX conformance.
