"""Portable account alias + consent-gated resolver (item-31).

A bank-neutral handle the user owns, resolved to a one-time routing token instead
of raw account coordinates — addressing and portability solved by the consent
layer. See :mod:`app.alias.resolver` for the honest-scope note.
"""

from __future__ import annotations

from .registry import Alias, AliasRegistry
from .resolver import (
    ROUTING_SCOPE,
    TOKEN_TTL,
    AliasResolver,
    Resolution,
    RoutingCoordinates,
    coordinates_for,
)

__all__ = [
    "Alias",
    "AliasRegistry",
    "AliasResolver",
    "Resolution",
    "RoutingCoordinates",
    "ROUTING_SCOPE",
    "TOKEN_TTL",
    "coordinates_for",
]
