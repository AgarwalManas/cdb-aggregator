# Threat model

For a system whose whole point is *trustworthy, auditable consent*, the trust
boundaries and integrity guarantees are part of the design — so they're written
down. This is a concise threat model for `cdb-aggregator`: what it protects, the
boundaries it protects them across, the threats considered and how the
architecture answers them, and what real FDX accreditation would additionally
require. It is scoped to the architecture demonstrated here (mock sources,
in-memory-by-default stores, no real end-user authentication); the honest limits
are called out throughout.

## Assets

- **Consent grants** — the record of who may see what, for how long. The most
  security-critical object: a wrong answer here is a data breach.
- **Customer financial data** — accounts, balances, transactions, holdings,
  identity/contact.
- **Access tokens** — bearer credentials to the (mock) data providers.
- **The audit trail** — the tamper-evident record of every access. Its value is
  that it is complete and unaltered.
- **Routing tokens** (item-31) — one-time, short-TTL references an alias resolves
  to instead of raw institution/transit/account. Single-use and never encode the
  coordinates, so a leaked token exposes nothing and cannot be replayed.
- **The attestation signing key** (item-32/33, *simulated*) — a symmetric **demo**
  key, deliberately not a secret. A real issuer would hold an asymmetric private
  key and publish only the verifying key; called out below and in-product.

## Trust boundaries

```
 Browser ──(1)──▶ Aggregator API ──(2)──▶ Consent gate ──(3)──▶ Adapters ──(4)──▶ Data providers
   │                    │                     │                                        │
 session cookie   per-session world   the single choke point                    OAuth2 (PAR+PKCE)
```

1. **Browser ↔ API.** Untrusted client. Requests carry a `SameSite=Lax`,
   `HttpOnly` session cookie that selects the caller's demo world. No end-user
   authentication in the demo — see *Limitations*.
2. **API ↔ gate.** Every data read is funnelled through `ConsentEnforcingReader`;
   there is no un-gated path to the adapters. The gate is the trust boundary that
   turns "authenticated" into "authorized for *this* scope and account".
3. **Gate ↔ adapters.** The gate decides; the adapters fetch. Adapters never see
   a request the gate didn't clear, and their output is minimized before return.
4. **Adapters ↔ providers.** Token-based access (OAuth2). Credentials never
   transit the aggregator on behalf of the user (contrast: screen-scraping).

## Threats and mitigations (STRIDE)

| Threat | Vector | Mitigation |
|---|---|---|
| **Spoofing** | Forged/stolen provider token | Short-TTL bearer tokens; **PKCE (S256) + PAR** bind the authorization to the client (item-23); tokens validated per request. Confidential-client auth on token/PAR. |
| **Tampering** | Altering/deleting an audit entry | **Hash-chained** audit log: each entry hashes its content + the prior hash, so any edit/deletion breaks the chain; `verify()` (and `GET /api/audit/verify`) detects it (item-22). Append-only interface — no delete/update. |
| **Repudiation** | "That access never happened" | Every read, **allowed *or* denied**, is logged against the grant it relied on, with actor attribution (aggregator vs delegated agent) — item-8/11. |
| **Information disclosure** | Returning more than was consented | **Consent gate** blocks any read without an active, in-scope, account-covering grant; **field-level minimization** strips ungranted clusters; excluded balances are shown as *excluded*, not leaked. Invariants are property-tested (item-24). |
| **Denial of service** | Flooding the API / unbounded growth | Session store is **LRU-bounded**; audit API paginates. Real rate limiting is out of scope (see below). |
| **Elevation of privilege** | Using one scope to reach another | Scope is checked per read with a distinct `SCOPE_NOT_GRANTED` / `ACCOUNT_NOT_COVERED` denial; a delegated agent is *just another consent*, held to the same gate. |

## Token & consent handling

- **Tokens** are short-lived bearer tokens from the mock provider, obtained via
  the FAPI-shaped **PAR → authorize → authorization-code + PKCE** flow; the
  `request_uri` and authorization code are single-use and short-lived. The
  **remaining FAPI gap is sender-constrained tokens** (mTLS or DPoP) — the mock
  issues plain bearer tokens (documented in the provider README).
- **Consent** is scoped, time-limited, and revocable. Revocation is terminal and
  immediate; expiry is computed from the clock, not a stored flag. The gate
  returns a *reason* for every denial, so transparency doesn't leak more than the
  decision itself.

## Audit-log integrity

- **Append-only + hash-chained** (item-22): the chain makes the log tamper-*evident*
  — you can prove no entry was changed after the fact, up to the current head.
- **Durable** backend available (item-25): `SqliteAuditLog` persists the chain so
  it survives a restart, behind the same interface as the in-memory log.
- **Known limitation:** a hash chain detects alteration but a determined actor
  with write access to the store could recompute *all* downstream hashes. Real
  tamper-*resistance* requires periodically **anchoring the head hash in external,
  append-only storage** (or notarizing it) so a full rewrite is detectable. Out of
  scope here; called out as the next step.

## Limitations (demo scope, by design)

- **No end-user authentication / authorization** on the aggregator itself — a
  session cookie selects a sandbox world; there is no login. Production needs real
  authn (and the gate would sit *behind* it, not instead of it).
- **No transport security in-app** — TLS is assumed to be terminated by the host
  (the live deploy runs behind HTTPS); the app does not manage certificates.
- **Mock providers, in-memory-by-default stores**; `CLIENT_SECRET` is a fixed
  local value, not a managed secret.
- **No rate limiting, no CSRF tokens** (state-changing calls are same-origin and
  cookie-guarded, but a production build would add CSRF defense and rate limits).
- **Selective-disclosure proofs and the credential wallet are simulated**
  (item-32/33). Facts are computed server-side and signed with a symmetric demo
  key (HMAC) — tamper-evident for the demo, but **not** a zero-knowledge proof and
  not an asymmetric issuer signature. Real deployment: SD-JWT VC / range proofs,
  asymmetric keys, and OID4VP transport. The alias resolver (item-31) demonstrates
  the addressing pattern only — every resolution is consent-gated and logged, but
  it settles nothing and is not a central registry.

## What real FDX accreditation would require

- **Full FAPI**: OAuth 2.0 + FAPI with **sender-constrained tokens** (mTLS or
  DPoP), signed request objects, and a real user-authentication + consent
  redirect, against accredited providers; proper key management and token
  lifecycle.
- **Tamper-resistant audit**: hash chain **plus external anchoring / notarization**
  of the head, on durable append-only storage.
- **Persistence & secrets**: a real database behind the store interfaces (the
  SQLite audit backend is the first step), managed secrets, encryption at rest.
- **Operational security**: authn/authz on the API, CSRF protection, rate
  limiting, input hardening, a security review + threat-model refresh, monitoring
  and incident response, and data-residency controls.

> This document is part of building security-critical software responsibly: it
> records the reasoning, not a claim of certified security.
