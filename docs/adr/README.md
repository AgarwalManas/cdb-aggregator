# Architecture Decision Records

Short records of the decisions that shaped this project — the *why* behind the
structure, captured close to when the choice was made. Each ADR states the
context, the decision, the alternatives weighed, and the consequences.

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-backend-fastapi.md) | Backend framework: FastAPI (Python) | Accepted |
| [0002](0002-fdx-aligned-canonical-model.md) | An FDX-aligned canonical model, `Decimal` money, camelCase wire format | Accepted |
| [0003](0003-consent-as-a-gate.md) | Consent as a gate every read passes, not scattered checks | Accepted |
| [0004](0004-traceability-and-minimization.md) | Append-only audit log + field-level data minimization | Accepted |
| [0005](0005-agentic-delegation-as-consent.md) | Model agent delegation as a consent to an agent identity | Accepted |
| [0006](0006-in-memory-stores-and-mocks.md) | In-memory stores + mock providers (no database yet) | Accepted |

Format is loosely [Michael Nygard's](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
