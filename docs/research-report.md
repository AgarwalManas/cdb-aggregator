# Context — Canada's Consumer-Driven Banking and the FDX Standard

Background and references for why this project is built the way it is: **FDX-first**,
with **consent and traceability** as the core rather than an afterthought. This is a
technical demonstration of the architecture open banking calls for; it is not a live
integration with any institution or regulator (see [Scope](#scope-and-honesty)).

## Consumer-driven banking in Canada

Consumer-driven banking — also called open banking — is a framework that lets people
and businesses direct their financial institution to securely share their data with
service providers of their choice, over APIs, instead of by handing over banking
credentials.

Canada's framework moved from proposal to law recently. **Bill C-15 (the Budget
Implementation Act, 2025, No. 1) received Royal Assent on March 26, 2026**, replacing
the original Consumer-Driven Banking Act with a comprehensive new **Consumer-Driven
Banking Act (CDBA)**. Oversight sits with the **Bank of Canada**, building on its
existing supervisory role for payment service providers under the Retail Payment
Activities Act; the Department of Finance leads regulation development. The Bank of
Canada is responsible for accrediting participants and maintaining a public registry
of accredited entities.

Implementation is planned in two phases:

- **Phase 1 — read access** (account information sharing), targeted for early 2026.
- **Phase 2 — write access** (payment initiation, account switching), targeted for
  mid-2027 and contingent on Canada's Real-Time Rail being live and in wide use.

Timing is genuinely uncertain: as of early 2026 the Bank of Canada had not committed
to a firm Phase-1 launch date. This project is built **for** that world (read-first,
FDX-shaped), not on a claim to be certified within it.

## The problem it replaces: screen scraping

Historically, aggregation in Canada has relied on **screen scraping** — a service
logging into a consumer's bank on their behalf using stored credentials. The
Government of Canada has noted that roughly nine million Canadians share data this way,
carrying elevated security, liability, and privacy risk. Screen scraping is brittle
(it breaks when a bank changes its login flow) and it grants far more access than any
single feature needs. The CDBA is explicit about moving past it — under the Act,
screen scraping is prohibited once the framework is operational.

This project takes the opposite starting point: **token-based access to an FDX-shaped
data model**, with consent that is scoped, time-limited, and revocable, and an
auditable record of every access.

## The FDX standard

The **Financial Data Exchange (FDX)** is a non-profit body maintaining a common,
interoperable, royalty-free API standard for user-permissioned financial data sharing,
focused on the US and Canada. It is organized around five core principles:

1. **Control** — consumers can grant, modify, and revoke access to their data.
2. **Access** — account owners can reach their data and decide who else may.
3. **Transparency** — clarity about who has access, for what, and for how long.
4. **Traceability** — the ecosystem can account for how data moved and why.
5. **Security** — permissioned, credential-free access built on secure standards.

Technically, FDX uses **OAuth 2.0** with the **FAPI** security profile and a defined
**consent** model (a consent grant is the record that a data recipient may access a
consumer's data, subject to the consumer's control and revocation). The specification
is royalty-free to implement under FDX's license terms.

Those five principles are the backbone of this project's design. The consent gate
maps to Control and Access; the audit trail to Traceability and Transparency; the
token-based, credential-free access and field-level minimization to Security.

## Consent, traceability, and data minimization

The reason this project makes consent its centerpiece — rather than a settings screen
bolted onto an aggregator — is that consent and traceability are what distinguish an
accredited, standards-native participant from a credential-based scraper. The
implementation reflects that:

- **Scoped, time-limited, revocable consent**, enforced at a single gate every read
  passes through.
- **An append-only audit trail** tying each access to the grant it relied on, recording
  what was disclosed and what was withheld.
- **Data minimization** — a read returns only the fields the granted scopes permit.

## Where the standard is heading: agentic delegation

In April 2026, FDX launched an initiative focused on **agentic AI** in financial data
sharing — examining agent identity, consent and delegation, data minimization,
downstream accountability, and traceability as AI agents begin acting on a consumer's
behalf. This project's delegation feature is built in that spirit: a task handed to an
agent is modeled as *another consent* — scoped, revocable, logged, and suggestion-only
— so the governance around a delegated actor is the same governance applied to any
data access.

## Scope and honesty

- This is a working demonstration of the **architecture**: a canonical FDX-shaped
  model, adapters that normalize varied sources into it, and a consent layer that
  gates, logs, and minimizes every read.
- It is **not** a live or certified integration. Data sources are mocks; persistence
  is in-memory by default. It models the standard, on the parts it covers, rather than
  claiming accreditation that doesn't exist yet.
- It is built **for** Canada's read-first Phase 1, with a credible path toward the
  write-access and payment-initiation concerns of Phase 2.

## References

- Financial Data Exchange — About & five core principles:
  <https://financialdataexchange.org/about-fdx/>
- Financial Data Exchange — home / standard & news (incl. April 14, 2026 agentic-AI
  initiative): <https://financialdataexchange.org/>
- Bank of Canada — Consumer-driven banking (oversight):
  <https://www.bankofcanada.ca/regulatory-oversight/consumer-driven-banking/>
- Government of Canada — Budget 2025: Canada's Consumer-Driven Banking Framework:
  <https://www.canada.ca/en/department-finance/programs/financial-sector-policy/open-banking-implementation/budget-2025-canadas-framework-for-consumer-driven-banking.html>
- CFPB — recognition of FDX as an open-banking standard-setting body:
  <https://www.consumerfinance.gov/about-us/newsroom/cfpb-approves-application-from-financial-data-exchange-to-issue-standards-for-open-banking/>

*Regulatory details summarized here reflect public sources as of mid-2026 and are
provided for context, not as legal advice.*
