# syntax=docker/dockerfile:1
#
# One image that serves both the API and the built React UI, so a single
# service hosts the whole app (that's what the "try it live" deploy runs).
#
#   Stage 1 (web)  — compile the React app to static files with Node.
#   Stage 2 (final) — Python runtime that serves the API *and* those files.

# ---- Stage 1: build the frontend ------------------------------------------
FROM node:20-slim AS web
WORKDIR /web

# Install deps first so this layer caches unless the lockfile changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build            # -> /web/dist

# ---- Stage 2: the runtime image -------------------------------------------
FROM python:3.11-slim AS final
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install the backend. Copy only what pip needs first for layer caching.
COPY pyproject.toml README.md ./
COPY backend/ ./backend/
RUN pip install .

# Bring in the compiled UI and point the app at it.
COPY --from=web /web/dist ./frontend/dist
ENV CDB_FRONTEND_DIST=/app/frontend/dist \
    CDB_ENVIRONMENT=production \
    CDB_DEBUG=false

# The platform injects $PORT; default to 8000 for plain `docker run`.
ENV PORT=8000
EXPOSE 8000

# Shell form so ${PORT} is expanded at container start.
CMD uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT}
