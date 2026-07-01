# Post drafts

Two ready-to-adapt drafts for sharing the project publicly: a short LinkedIn post
and a longer blog outline. Swap in the repo URL and a screenshot or two.

---

## LinkedIn post (short)

> Canada's open-banking framework just became law — Bill C-15 got Royal Assent in
> March 2026, replacing the old act with a new Consumer-Driven Banking Act under
> the Bank of Canada. So I built the thing that transition actually needs.
>
> **cdb-aggregator** is an FDX-aligned account aggregator, but the point isn't the
> aggregation — it's the **consent + traceability layer** underneath it. The part
> that separates an accredited open-banking participant from an app that stores
> your bank password and scrapes your statements.
>
> What it does:
> • Normalizes three deliberately different sources — a clean FDX bank, a messy
>   legacy system, and a screen-scraped website — into one canonical model.
> • Gates **every** data read on an active, in-scope, revocable consent. No grant,
>   no data — with a specific reason why.
> • Logs every access (allowed *or* denied) to an append-only trail, and returns
>   only the fields you actually shared. A balance you didn't share drops out of
>   your net worth — surfaced as excluded, not silently.
> • Extends the same consent machinery to govern an **AI agent**: a scoped,
>   revocable, fully-logged delegation that suggests a move for your idle cash but
>   never acts. Revoke it and it's powerless.
>
> Built FDX-first and honest about scope: it models the standard, it doesn't claim
> certified connectivity. Python/FastAPI + React, 100% test coverage enforced in
> CI, decisions documented as ADRs.
>
> The bet: in a consumer-driven-banking world, the moat isn't aggregation — it's
> trustworthy, auditable consent.
>
> Repo + write-up 👇 [link]
>
> #OpenBanking #FDX #ConsumerDrivenBanking #Fintech #Python #React

---

## Blog outline (longer)

**Title:** *Building for consumer-driven banking: why the consent layer is the
product*

1. **The moment.** Bill C-15 / the new CDBA, Bank of Canada oversight, FDX as the
   standard, Phase-1/Phase-2 timing. Set the stage in two paragraphs.
2. **The problem with the status quo.** Screen-scraping and credential sharing:
   how it works, why it's brittle, why it's all-or-nothing. The documented pain
   (failed connections, no revocation that isn't a password change). Link to the
   [screen-scraping explainer](screen-scraping.md).
3. **The thesis.** In an accredited, consent-based world, the differentiator isn't
   who can aggregate — it's who can prove *trustworthy, auditable consent*. So make
   that the core, not a feature.
4. **The architecture.** Three sources → adapters/normalizer → one FDX-aligned
   canonical model → the consent gate → dashboards + agent. Why the gate is a
   single choke point, not scattered checks.
5. **The consent layer, in depth.** Granular scopes, expiry, one-tap revoke;
   decisions that carry a reason; append-only audit; field-level minimization.
   Screenshot: the traceability log with a denied access.
6. **The twist: governing an AI agent.** Delegation modelled as a consent to an
   agent identity — scoped, revocable, logged, suggestion-only. Why that maps onto
   FDX's 2026 agentic-AI themes, and why the engine being deterministic is a
   feature, not a gap. Screenshot: the Assistant tab.
7. **Trade-offs and what production would need.** Mocks + in-memory stores by
   design; the path to accreditation (real OAuth/FAPI, tamper-evident audit,
   persistence behind the existing interfaces, security review). Link to the
   [ADRs](adr/).
8. **Engineering notes.** 100% coverage + warnings-as-errors in CI; the build as a
   tagged timeline (`item-01 … item-14`); building with AI tooling, reviewed like
   an owner.
9. **Close.** The one-line thesis, and an invitation to read the code.

**Assets to attach:** the net-worth Overview, the consent dashboard with the
denied audit row, and the Assistant suggestion.
