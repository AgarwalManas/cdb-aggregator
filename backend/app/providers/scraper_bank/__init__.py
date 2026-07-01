"""Screen-scraping mock provider (Item 6, stretch).

A mock online-banking *website* — login form + HTML statement page, no API. It
exists to be scraped, dramatizing the "old way" (credential sharing, fragile
HTML parsing) against the token-based FDX "new way". Paired with the scraper
adapter in :mod:`app.adapters.scraper_bank` and the contrast in
:mod:`app.comparison`.

Run it on its own::

    uvicorn app.providers.scraper_bank.app:app --app-dir backend --port 9003
"""

from __future__ import annotations

from .app import app, create_app

__all__ = ["app", "create_app"]
