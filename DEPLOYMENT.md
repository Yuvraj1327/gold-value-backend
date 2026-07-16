# Deployment Guide

## 1. Provision Supabase

1. Create a project at [supabase.com](https://supabase.com).
2. Note down (Project Settings -> API): Project URL, `anon` key,
   `service_role` key, and JWT Secret.
3. Note down (Project Settings -> Database): the connection string —
   prefer the **Transaction pooler** (port 6543) for serverless/many-instance
   deployments, or the **Session pooler** (port 5432) for a single
   long-lived backend process.
4. Enable the auth providers you need (Dashboard -> Authentication ->
   Providers): Email, Google, and **Anonymous sign-ins** (toggle in
   Authentication -> Settings -> "Allow anonymous sign-ins") for the guest
   login flow.

## 2. Apply the schema

From your local machine (with `.env` pointed at the real Supabase DB):

```bash
cd backend
alembic upgrade head
```

This applies both migrations: the initial schema, and the follow-up
migration adding `role` (role-based authorization), `ltv_percent` and the
wastage/making-charges/GST/`final_value` columns to `calculations`, and
the new default-charge/notification columns on `settings`.

Then run `supabase/schema.sql` once via the Supabase SQL Editor (creates
the auto-profile trigger + RLS policies — see that file's header comment
for why it's separate from Alembic). That same file's §4 also has the
one-line SQL to bootstrap your first admin user (there is no self-service
"become admin" API endpoint, by design).

## 3. Choose a hosting target

Any platform that runs a long-lived Docker container or ASGI process
works. Two straightforward options:

### Option A — Railway / Render / Fly.io (simplest)

1. Push this `backend/` folder to its own Git repo (or a monorepo with
   root set to `backend/`).
2. Create a new "Web Service" from the repo; these platforms auto-detect
   the `Dockerfile`.
3. Set all variables from `.env.example` as environment variables in the
   platform's dashboard — **never** commit `.env`.
4. Set the start command to the Dockerfile's default (migrations run
   automatically on boot via the `CMD`), or split into a release step +
   start command if the platform supports it:
   - Release: `alembic upgrade head`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4`
5. Point the Flutter app's `API_BASE_URL` at the platform-provided HTTPS URL.

### Option B — Self-managed (VPS + Docker)

```bash
docker build -t gold-value-calculator-api .
docker run -d \
  --name gvc-api \
  --env-file .env \
  -p 8000:8000 \
  --restart unless-stopped \
  gold-value-calculator-api
```

Put this behind Nginx/Caddy for TLS termination (HTTPS is required — the
Flutter app sends bearer tokens that must never travel over plain HTTP in
production).

## 4. Multi-instance scheduler note

`app/services/scheduler.py` runs the hourly gold-rate refresh **in-process**
via APScheduler. This is fine for a single instance. If you scale to
multiple instances/replicas:

- **Simplest fix:** run exactly one replica with the scheduler enabled and
  route it no differently from the others (it still serves normal API
  traffic) — set an env flag like `ENABLE_SCHEDULER=true` only on that one
  instance if you want to guard against duplicate writes when scaling out.
- **More robust fix:** move the refresh job to a platform-native cron
  (Railway Cron Jobs, a Kubernetes CronJob, GitHub Actions scheduled
  workflow hitting an internal `/internal/refresh-gold-rate` endpoint,
  etc.) and remove the in-process scheduler entirely.

Either way, duplicate writes are harmless (each is just a new `gold_rates`
row) — the only downside is wasted provider API calls.

## 5. Environment checklist before going live

- [ ] `APP_ENV=production`, `DEBUG=false`
- [ ] `CORS_ORIGINS` set to your actual Flutter app's origin(s) — never `*`
      in production
- [ ] `SUPABASE_JWT_SECRET` matches the value in Supabase Dashboard exactly
- [ ] `GOLD_RATE_API_KEY` set to a real provider key with sufficient quota
      for `24 * (60 / GOLD_RATE_REFRESH_INTERVAL_MINUTES)` calls/day
- [ ] Database connection uses SSL (Supabase pooler URLs do by default)
- [ ] Logs (`LOG_JSON=true`) are shipped somewhere queryable (most PaaS
      platforms capture stdout automatically)
- [ ] `/docs` and `/redoc` — decide whether to keep them public or gate
      them behind an internal-only route/IP allowlist for a production
      fintech app

## 6. CI/CD

`.github/workflows/backend-ci.yml` runs on every push/PR touching
`backend/`: ruff lint, mypy (non-blocking), and pytest with coverage. Wire
a deploy step at the end once you've picked a hosting target — most
platforms (Railway, Render, Fly.io) support "deploy on push to main"
natively without needing a custom GitHub Actions deploy job.
