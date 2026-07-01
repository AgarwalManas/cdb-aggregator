"""Source adapters / normalizers (Item 5).

One adapter per provider, each mapping that provider's raw shape into the
canonical FDX model (``app.models``) behind a common interface
(:class:`SourceAdapter`). Taming real-world schema drift is the point, so the
mappers are pure functions and each adapter is unit-tested.

    from app.adapters import FdxBankAdapter, LegacyBankAdapter

Each adapter takes a :class:`SourceClient` (transport). Concrete HTTP clients —
``FdxHttpClient`` / ``LegacyHttpClient`` — live alongside their adapters.
"""

from __future__ import annotations

from .base import (
    NormalizationError,
    SourceAdapter,
    SourceClient,
    SourceSnapshot,
)
from .fdx_bank import FdxBankAdapter, FdxHttpClient
from .legacy_bank import LegacyBankAdapter, LegacyHttpClient

__all__ = [
    "SourceAdapter",
    "SourceClient",
    "SourceSnapshot",
    "NormalizationError",
    "FdxBankAdapter",
    "FdxHttpClient",
    "LegacyBankAdapter",
    "LegacyHttpClient",
]
