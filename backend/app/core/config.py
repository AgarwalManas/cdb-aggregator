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

    # Mock data providers. Base URL of the FDX bank (Item 3); the Item 5 adapter
    # reads from here. The messy source (Item 4) will add its own entry.
    provider_fdx_base_url: str = "http://127.0.0.1:9001"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the env is parsed once per process; tests can clear the cache via
    `get_settings.cache_clear()` if they need to override values.
    """

    return Settings()
