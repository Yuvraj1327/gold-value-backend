# Gold Value Calculator — Backend

FastAPI backend for the Gold Value Calculator app: live gold rates, gold
value & gold loan calculations, per-user calculation history, and settings.
Backed by Supabase Postgres (via SQLAlchemy + Alembic) and Supabase Auth.

## Stack

| Concern | Choice |
|---|---|
| Framework | FastAPI (async) |
| Language | Python 3.13 |
| ORM | SQLAlchemy 2.0 (async, `asyncpg`) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| Auth | Supabase Auth (JWT verified locally via `python-jose`) |
| Rate limiting | slowapi |
| Scheduling | APScheduler (hourly gold rate refresh) |
| PDF reports | reportlab |
| Testing | pytest + pytest-asyncio (47 tests: pure-logic unit tests + fake-repository service tests + DB-independent endpoint tests) |

## Architecture

Clean Architecture, four layers:

```
app/
  api/            presentation — FastAPI routers, request/response wiring only
    v1/endpoints/
    deps.py        dependency-injection wiring (DB session -> repo -> service)
  services/       application/business logic — orchestrates repositories,
                  external calls (Supabase Auth, gold rate provider), and
                  pure calculation utilities
  repositories/   data access — all SQLAlchemy queries live here, nowhere else
  models/         SQLAlchemy ORM models (the persistence shape)
  schemas/        Pydantic request/response models (the API shape) —
                  deliberately separate from ORM models
  core/           config, security (JWT), exceptions, logging, middleware,
                  rate limiting
  database/       engine/session setup
  utils/          pure functions (calculation formulas, pagination) — no I/O
```

Dependency direction is strictly inward: `api` depends on `services`,
`services` depend on `repositories`, `repositories` depend on `models`.
Nothing in `services` or `repositories` imports from `api`.

## Getting started locally

### 1. Prerequisites

- Python 3.13
- A Supabase project (free tier is fine) — [supabase.com](https://supabase.com)
- (Optional) Docker, if you'd rather not install Python locally

### 2. Configure environment

```bash
cd backend
cp .env.example .env
```

Fill in `.env` with your Supabase project's values (Project Settings ->
API, and Project Settings -> Database -> Connection string). See
`.env.example` for exactly which fields and where to find each one.

### 3. Apply the database schema

```bash
pip install -r requirements-dev.txt

# Creates users, gold_rates, calculations, settings tables
alembic upgrade head
```

Then, in the Supabase SQL Editor (or via `psql`), run `supabase/schema.sql`
to add the auto-profile trigger and Row Level Security policies. This step
is separate from Alembic because it touches `auth.users`, which only exists
inside a real Supabase project (not a vanilla Postgres instance used in CI).

### 4. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs (Swagger) or `/redoc`
- Health check: http://localhost:8000/health

### 5. Run tests

```bash
pytest --cov=app --cov-report=term-missing
```

### Docker alternative

```bash
docker compose up --build
```

## Connecting the Flutter app

Set `API_BASE_URL` in the Flutter app's `.env` to wherever this backend is
reachable:
- Android emulator talking to your laptop: `http://10.0.2.2:8000`
- Physical device on the same network: `http://<your-machine-LAN-IP>:8000`
- Deployed: your real HTTPS URL (see `DEPLOYMENT.md`)

The Flutter app authenticates directly against Supabase Auth (email,
Google, or anonymous guest) and sends the resulting Supabase access token
as `Authorization: Bearer <token>` on every request — this backend verifies
that token locally (see `app/core/security.py`) rather than requiring a
separate login step against the API.

## Further docs

- [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md) — every endpoint, request/response shape, error format
- [`DEPLOYMENT.md`](./DEPLOYMENT.md) — production deployment options & checklist
- [`supabase/schema.sql`](./supabase/schema.sql) — RLS policies & auto-profile trigger
