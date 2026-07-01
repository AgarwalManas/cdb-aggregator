"""Per-visitor demo state.

The demo world (accounts, consents, the audit trail) is mutable — visitors
revoke connections, run the agent, grant new sources. If one shared instance
backed the whole app, a single visitor's changes would be visible to everyone
and would persist until the process restarted. That's wrong for a public link,
so **each browser session gets its own isolated copy of the world**, keyed by an
opaque cookie set by the session middleware.

The store is bounded with LRU eviction so a public URL can't grow memory without
limit: once the cap is reached the least-recently-used session is dropped, and
that visitor simply gets a fresh world on their next request — same as a first
visit. State is in-memory by design (see ADR 0006); this is the seam a real
per-user datastore would slot into.
"""

from __future__ import annotations

import secrets
from collections import OrderedDict

from fastapi import Request

from app.api.demo import AggregatorState, build_demo_state

SESSION_COOKIE = "cdb_session"
COOKIE_MAX_AGE = 60 * 60 * 24  # one day, in seconds
MAX_SESSIONS = 500  # cap on concurrently-tracked demo worlds


def new_session_id() -> str:
    """Return an unguessable session identifier."""
    return secrets.token_urlsafe(16)


class SessionStore:
    """In-memory map of session id → that visitor's demo world (LRU-bounded)."""

    def __init__(self, max_sessions: int = MAX_SESSIONS) -> None:
        self._worlds: OrderedDict[str, AggregatorState] = OrderedDict()
        self._max = max_sessions

    def __len__(self) -> int:
        return len(self._worlds)

    def get_or_create(self, session_id: str) -> AggregatorState:
        """Return the session's world, creating a fresh one on first sight."""
        world = self._worlds.get(session_id)
        if world is None:
            world = build_demo_state()
            self._worlds[session_id] = world
            self._evict()
        else:
            self._worlds.move_to_end(session_id)  # mark most-recently used
        return world

    def reset(self, session_id: str) -> AggregatorState:
        """Replace the session's world with a fresh one (the 'reset demo' action)."""
        world = build_demo_state()
        self._worlds[session_id] = world
        self._worlds.move_to_end(session_id)
        self._evict()
        return world

    def _evict(self) -> None:
        """Drop least-recently-used sessions until back within the cap."""
        while len(self._worlds) > self._max:
            self._worlds.popitem(last=False)


def get_state(request: Request) -> AggregatorState:
    """FastAPI dependency: the current visitor's demo world.

    The session middleware guarantees ``request.state.session_id`` is set before
    any route runs, so this just looks it up (creating on first sight).
    """
    store: SessionStore = request.app.state.sessions
    return store.get_or_create(request.state.session_id)
