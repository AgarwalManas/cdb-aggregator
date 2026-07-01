"""PKCE (RFC 7636) helpers.

Proof Key for Code Exchange binds an authorization code to the client that
requested it: the client sends a hashed ``code_challenge`` up front and proves it
holds the matching ``code_verifier`` when redeeming the code. FAPI mandates PKCE
with the ``S256`` method. Shared here so the mock authorization server and the
adapter that drives it agree on the transform.
"""

from __future__ import annotations

import base64
import hashlib
import secrets

CODE_CHALLENGE_METHOD = "S256"


def generate_verifier() -> str:
    """Return a fresh high-entropy ``code_verifier`` (RFC 7636 §4.1)."""
    return secrets.token_urlsafe(48)


def s256_challenge(verifier: str) -> str:
    """Return the S256 ``code_challenge`` for ``verifier``: base64url(sha256), unpadded."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
