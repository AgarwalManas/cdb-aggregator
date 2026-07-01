"""The screen-scraping mock's FastAPI app — a bank *website*, not an API.

* ``GET  /``          -> the login form (HTML)
* ``POST /login``     -> validate credentials, set a session cookie
* ``GET  /statement`` -> the HTML statement page (requires the cookie)

There is no JSON, no token, no scope. To get data out of it you must log in with
the customer's real credentials and parse the returned HTML — which is exactly
what the scraper adapter (Item 6) does, and exactly what open banking replaces.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Form
from fastapi.responses import HTMLResponse

from . import data
from .auth import (
    COOKIE_NAME,
    OLDBANK_PASS,
    OLDBANK_USER,
    Session,
    SessionStore,
    require_session,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="OldBank (screen-scraping mock)",
        version="0.0.0",
        summary="A credential-login bank website with no API — exists to be scraped.",
    )
    app.state.session_store = SessionStore()

    @app.get("/", response_class=HTMLResponse, tags=["web"], summary="Login form")
    def login_form() -> str:
        return data.LOGIN_FORM_HTML

    @app.post("/login", response_class=HTMLResponse, tags=["web"], summary="Sign in")
    def login(username: Annotated[str, Form()], password: Annotated[str, Form()]) -> HTMLResponse:
        if username != OLDBANK_USER or password != OLDBANK_PASS:
            return HTMLResponse("<p>Invalid credentials</p>", status_code=401)
        session = app.state.session_store.open()
        response = HTMLResponse('<p>Signed in. <a href="/statement">View statement</a></p>')
        # A plain session cookie — the entire "auth" story of the old way.
        response.set_cookie(COOKIE_NAME, session.sid, httponly=True)
        return response

    @app.get(
        "/statement",
        response_class=HTMLResponse,
        tags=["web"],
        summary="HTML statement (requires session cookie)",
    )
    def statement(_session: Annotated[Session, Depends(require_session)]) -> str:
        return data.render_statement_html()

    return app


#: Module-level instance for ``uvicorn app.providers.scraper_bank.app:app``.
app = create_app()
