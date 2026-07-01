# ADR 0005 — Model agent delegation as a consent to an agent identity

**Status:** Accepted (Item 11)

## Context

The differentiator is an *agentic delegation* layer: let a customer hand a task to
an AI agent. FDX's April-2026 Agentic-AI initiative names the hard parts — agent
identity, consent delegation, data minimization, downstream accountability, and
traceability. Those are precisely the concerns the consent engine already solves
for human-facing access.

## Decision

Model an agent delegation as **just another consent**, from the customer to an
**agent identity** (the recipient, e.g. `agent:cash-finder`):

- The agent reads through the **same** `ConsentEnforcingReader`, as the agent
  recipient — so every read is gated, minimized, and **logged against the agent**.
- The delegation is **scoped, time-limited, and revocable** like any grant; revoke
  it and the agent is powerless (its `run` returns 403).
- A delegation is **capped at what the customer shared with the aggregator** — you
  can't delegate access you don't have.
- The agent returns a **suggestion, not an action** (no write access), which keeps
  it honest about Canada's Phase-2 (write) open-banking timing.

The bundled engine (an idle-cash finder) is deterministic and unit-tested;
**swapping it for an LLM would not change the governance.**

## Alternatives

- **A bespoke agent-permission system** — rejected; it would re-implement scopes,
  expiry, revocation, minimization, and audit that already exist.
- **Give the agent broad, implicit access** — rejected; the whole point is that an
  autonomous actor is bound by the same consent as everyone else.

## Consequences

- Agent access is attributable in the audit log ("🤖 Assistant" vs the aggregator).
- The differentiator reuses the star feature instead of bolting on a side-system.
- Non-determinism and API cost are avoided by defaulting to a deterministic engine;
  an LLM-backed mode can be added behind a flag later.
