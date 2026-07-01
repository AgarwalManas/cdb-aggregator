# Project docs

Context and planning for the build. These travel with the repo so the work is
self-contained and any coding session (or reviewer) has the full picture.

- **roadmap.md** — the full build timeline: how the project was assembled, in
  dependency order, each Item landing as a tagged commit (`item-01` … `item-33`) —
  the core build plus the UI-refinement, hardening, and consent-frontier follow-on.
- **research-report.md** — the regulatory and standards context behind the design
  (CDBA, FDX, the screen-scraping problem), with references.
- **adr/** — architecture decision records: the *why* behind the key structural
  choices, one file per decision.
- **screen-scraping.md** — "why screen-scraping is about to break": the argument
  for building FDX-first, with the old-way/new-way contrast.
- **THREAT_MODEL.md** — trust boundaries, threats/mitigations, audit-log
  integrity, and what real FDX accreditation would require.
- **fdx-conformance.md** — which FDX entities/fields the mock provider is
  schema-validated against (drift fails the build), plus the canonical mapping.
- **project-review.md** — a walkthrough script (problem, architecture, the consent
  layer, trade-offs, path to accreditation, Q&A).

> These are planning artifacts, not claims of live regulatory integration. See
> the root README for scope.
