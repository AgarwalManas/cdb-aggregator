"""A bank-neutral alias the user owns, and the registry that holds it (item-31).

The alias (e.g. ``ada.cdb``) is an identifier the *user* controls; it points at
whichever account is their current routing target. Re-pointing it — portability —
is a first-class action, timestamped so the change is visible and (in the
resolver) logged as a scoped consent event.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Alias:
    """A handle the user owns, pointing at their current routing target."""

    handle: str
    account_id: str
    created_at: datetime
    repointed_at: datetime | None = None


class AliasRegistry:
    """The user's aliases, keyed by handle. In-memory, like the rest of the demo."""

    def __init__(self) -> None:
        self._by_handle: dict[str, Alias] = {}

    def register(self, handle: str, account_id: str, *, at: datetime) -> Alias:
        alias = Alias(handle=handle, account_id=account_id, created_at=at)
        self._by_handle[handle] = alias
        return alias

    def repoint(self, handle: str, account_id: str, *, at: datetime) -> Alias:
        """Point an existing alias at a different account. Raises if unknown."""
        alias = self._by_handle[handle]
        alias.account_id = account_id
        alias.repointed_at = at
        return alias

    def get(self, handle: str) -> Alias | None:
        return self._by_handle.get(handle)

    def all(self) -> list[Alias]:
        return list(self._by_handle.values())
