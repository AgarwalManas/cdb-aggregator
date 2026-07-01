"""Application configuration.

Settings are read from environment variables (and an optional `.env` file) so
that nothing environment-specific is baked into the code. See `.env.example` at
the repo root for the available knobs.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Extend this as later phases land (e.g. database URL for the audit log in
    Item 8, mock-provider base URLs for Items 3-4). Keeping config centralized
    and typed is part of the "keep it simple, make it obvious" goal.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CDB_",
        extra="ignore",
    )

    # Identity / metadata
    app_name: str = "Consumer-Driven Banking Aggregator"
    environment: str = "local"
    debug: bool = True

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Optional path to the built React app (frontend/dist). When set to a real
    # directory, the API also serves the single-page app at "/", so one process
    # hosts both the API and the UI — that's what the container deploy uses
    # (CDB_FRONTEND_DIST). Unset in local dev, where Vite serves the UI on 5173.
    frontend_dist: str | None = None

    # Mock data providers. Base URLs the Item 5 adapters read from: the clean
    # FDX bank (Item 3) and the messy legacy bank (Item 4).
    provider_fdx_base_url: str = "http://127.0.0.1:9001"
    provider_legacy_base_url: str = "http://127.0.0.1:9002"
    provider_scraper_base_url: str = "http://127.0.0.1:9003"  # screen-scraping mock (Item 6)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the env is parsed once per process; tests can clear the cache via
    `get_settings.cache_clear()` if they need to override values.
    """

    return Settings()
