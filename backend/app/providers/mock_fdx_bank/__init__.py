"""Mock FDX-compliant data provider (Item 3).

A small, standalone "bank" that behaves like an FDX data provider: it issues
OAuth2 access tokens and serves **FDX-shaped JSON** from Bearer-protected
resource endpoints. It is the *clean, standards-native* source — the easy case
for the normalizer (Item 5), in deliberate contrast to the messy source built in
Item 4.

Run it on its own (separate process from the aggregator)::

    uvicorn app.providers.mock_fdx_bank.app:app --app-dir backend --port 9001

It is intentionally decoupled from ``app.models`` (the aggregator's canonical
model): a real bank doesn't import our types. The adapter in Item 5 is what maps
this provider's FDX JSON into the canonical model.
"""

from __future__ import annotations

from .app import app, create_app

__all__ = ["app", "create_app"]
