# Project docs

Context and planning for the build. These travel with the repo so the work is
self-contained and any coding session (or reviewer) has the full picture.

- **build-todo.md** — the build roadmap: how the project was assembled, in
  dependency order, each Item landing as a tagged commit (`item-01` … `item-14`).
- **polish-todo.md** — the follow-on roadmap: a UI-refinement pass and a set of
  technical-hardening items (`item-15` onward), same tag convention.
- **research-report.md** — the regulatory and standards context behind the design
  (CDBA, FDX, the screen-scraping problem), with references.
- **adr/** — architecture decision records: the *why* behind the key structural
  choices, one file per decision.
- **screen-scraping.md** — "why screen-scraping is about to break": the argument
  for building FDX-first, with the old-way/new-way contrast.
- **project-review.md** — a walkthrough script (problem, architecture, the consent
  layer, trade-offs, path to accreditation, Q&A).
- **blog-post.md** — LinkedIn + blog drafts for sharing the project publicly.

> These are planning artifacts, not claims of live regulatory integration. See
> the root README for scope.
