-- =============================================================================
-- Gold Value Calculator — Supabase-specific SQL
-- =============================================================================
-- Run this AFTER applying the Alembic migrations (which create the base
-- tables: users, gold_rates, calculations, settings). This file adds the
-- Supabase-specific pieces that don't belong in Alembic: the trigger that
-- keeps public.users in sync with auth.users, and Row Level Security (RLS)
-- policies so Postgres itself enforces per-user data isolation — this is
-- what makes it safe for the Flutter app to eventually query Supabase
-- directly (e.g. via realtime subscriptions) without bypassing the backend.
--
-- Apply via: Supabase Dashboard -> SQL Editor -> paste & run,
-- or: psql "$DATABASE_URL" -f supabase/schema.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Auto-create a public.users profile row whenever a new auth.users row
--    is created (covers email/password, Google OAuth, and anonymous guest
--    sign-ups alike).
-- -----------------------------------------------------------------------------
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, email, name, created_at)
  values (
    new.id,
    coalesce(new.email, new.id::text || '@anonymous.local'),
    new.raw_user_meta_data ->> 'name',
    now()
  )
  on conflict (id) do update
    set email = excluded.email;

  insert into public.settings (user_id)
  values (new.id)
  on conflict (user_id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_auth_user();

-- -----------------------------------------------------------------------------
-- 2. Row Level Security
-- -----------------------------------------------------------------------------
alter table public.users enable row level security;
alter table public.gold_rates enable row level security;
alter table public.calculations enable row level security;
alter table public.settings enable row level security;

-- users: a user can only read/update their own profile row.
drop policy if exists "users_select_own" on public.users;
create policy "users_select_own"
  on public.users for select
  using (auth.uid() = id);

drop policy if exists "users_update_own" on public.users;
create policy "users_update_own"
  on public.users for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- gold_rates: readable by any authenticated (or anonymous/guest) caller;
-- writes only ever happen from the backend using the service_role key,
-- which bypasses RLS entirely — so no insert/update policy is granted here.
drop policy if exists "gold_rates_select_all" on public.gold_rates;
create policy "gold_rates_select_all"
  on public.gold_rates for select
  using (true);

-- calculations: strictly scoped to the owning user for every operation.
drop policy if exists "calculations_select_own" on public.calculations;
create policy "calculations_select_own"
  on public.calculations for select
  using (auth.uid() = user_id);

drop policy if exists "calculations_insert_own" on public.calculations;
create policy "calculations_insert_own"
  on public.calculations for insert
  with check (auth.uid() = user_id);

drop policy if exists "calculations_update_own" on public.calculations;
create policy "calculations_update_own"
  on public.calculations for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "calculations_delete_own" on public.calculations;
create policy "calculations_delete_own"
  on public.calculations for delete
  using (auth.uid() = user_id);

-- settings: strictly scoped to the owning user.
drop policy if exists "settings_select_own" on public.settings;
create policy "settings_select_own"
  on public.settings for select
  using (auth.uid() = user_id);

drop policy if exists "settings_update_own" on public.settings;
create policy "settings_update_own"
  on public.settings for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "settings_insert_own" on public.settings;
create policy "settings_insert_own"
  on public.settings for insert
  with check (auth.uid() = user_id);

-- -----------------------------------------------------------------------------
-- 3. Notes
-- -----------------------------------------------------------------------------
-- The FastAPI backend connects using the Session/Transaction pooler
-- connection string (a plain Postgres role), NOT the anon/service_role
-- REST API — so these RLS policies do not restrict the backend's own
-- queries. They exist as defense-in-depth for any direct
-- Supabase client access (e.g. future realtime features) and as
-- documentation of the intended access model. The backend is still
-- responsible for its own authorization checks (see
-- app/services/history_service.py's `_get_owned` ownership check).

-- -----------------------------------------------------------------------------
-- 4. Bootstrapping the first admin (role-based authorization)
-- -----------------------------------------------------------------------------
-- Every user is created with role='user' (see public.users.role's column
-- default). There is deliberately NO API endpoint to self-promote to
-- admin — PUT /api/v1/admin/users/{id}/role requires an existing admin's
-- token. To create your very first admin, sign up normally through the
-- app, then run this once via the Supabase SQL Editor:
--
--   update public.users set role = 'admin' where email = 'you@example.com';
--
-- After that, use PUT /admin/users/{id}/role (as that admin) to promote
-- anyone else — no further direct SQL should be needed.
