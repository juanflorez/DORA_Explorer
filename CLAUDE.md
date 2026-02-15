# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AzTrial is a full-stack web application with a **FastAPI** (Python) backend and a **React** (TypeScript) frontend.

## Architecture

```
backend/          Python FastAPI backend
  app/
    main.py       FastAPI app entry point, middleware, router mounting
    api/routes.py API route handlers
    core/config.py Pydantic settings (env vars prefixed AZTRIAL_)
    models/       Pydantic models
  tests/          pytest tests using httpx AsyncClient
frontend/         React TypeScript frontend (Vite)
  src/
    App.tsx       Root component
    main.tsx      Entry point
```

The frontend proxies `/api` and `/health` requests to the backend at `localhost:8000` during development (configured in `vite.config.ts`).

## Backend Commands

All backend commands run from `backend/`:

```bash
# Install dependencies
pip install -e ".[dev]"

# Run dev server
uvicorn app.main:app --reload

# Run all tests
pytest

# Run a single test
pytest tests/test_main.py::test_health

# Lint
ruff check .

# Format
ruff format .
```

## Frontend Commands

All frontend commands run from `frontend/`:

```bash
# Install dependencies
npm install

# Run dev server (port 5173, proxies API to backend)
npm run dev

# Build for production
npm run build

# Lint
npm run lint
```

## Key Conventions

- Backend settings use `pydantic-settings` with `AZTRIAL_` env prefix
- Backend tests use `httpx.AsyncClient` with `ASGITransport` (no running server needed)
- pytest is configured with `asyncio_mode = "auto"` — async test functions work without decorators
- Ruff is the sole Python linter/formatter (configured in `pyproject.toml`)
- Vite proxies `/api` to the backend in dev mode — frontend fetches use relative paths like `/api/hello`
