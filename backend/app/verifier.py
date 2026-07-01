"""Verifiable-presentation checking — the verifier side of the wallet (item-33).

**Simulated.** Item 32 lets the holder issue signed attestations of derived
facts; this is the counterparty that *receives* a selectively-disclosed subset of
them and decides accept / reject against a policy. Each demo verifier declares
which facts it needs; :func:`present` verifies every presented credential's
signature and checks the policy, disclosing only whether each requirement was
met — never the data.

It is a demonstration of the OID4VP-style holder → verifier flow on mock data,
not a real credential wallet or verifier deployment. A production version would
use W3C VC / OID4VP with asymmetric issuer keys.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.attestation import FACTS, verify


@dataclass(frozen=True)
class Requirement:
    fact_id: str
    expected: bool  # the fact must hold (True) — or must not (False)


@dataclass(frozen=True)
class Verifier:
    verifier_id: str
    name: str
    purpose: str
    requirements: tuple[Requirement, ...]


VERIFIERS: dict[str, Verifier] = {
    "rental": Verifier(
        verifier_id="rental",
        name="Rental application (demo)",
        purpose="A landlord checking you can comfortably cover rent",
        requirements=(Requirement("liquid_10k", True), Requirement("no_overdraft", True)),
    ),
    "lender": Verifier(
        verifier_id="lender",
        name="Credit check (demo)",
        purpose="A lender assessing basic creditworthiness",
        requirements=(Requirement("no_overdraft", True), Requirement("salary_here", True)),
    ),
}


def _evaluate(requirement: Requirement, attestations: list[dict]) -> tuple[bool, str]:
    """Decide whether a requirement is met by the presented credentials."""
    presented = [a for a in attestations if a.get("fact_id") == requirement.fact_id]
    valid = [a for a in presented if verify(a)[0]]
    if any(a["holds"] == requirement.expected for a in valid):
        return True, "Satisfied by a valid attestation."
    if valid:
        return False, "Presented, but the fact does not hold as required."
    if presented:
        return False, "Presented, but the signature failed verification."
    return False, "Not presented."


def present(verifier_id: str, attestations: list[dict]) -> dict:
    """Check a selectively-disclosed presentation against a verifier's policy."""
    verifier = VERIFIERS[verifier_id]
    results = []
    for requirement in verifier.requirements:
        satisfied, detail = _evaluate(requirement, attestations)
        results.append(
            {
                "fact_id": requirement.fact_id,
                "question": FACTS[requirement.fact_id].question,
                "expected": requirement.expected,
                "satisfied": satisfied,
                "detail": detail,
            }
        )
    accepted = all(r["satisfied"] for r in results)
    return {
        "verifier_id": verifier.verifier_id,
        "verifier_name": verifier.name,
        "accepted": accepted,
        "presented_count": len(attestations),
        "results": results,
    }
