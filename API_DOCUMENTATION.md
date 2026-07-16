# API Documentation

Base URL: `{API_BASE_URL}/api/v1` (e.g. `http://localhost:8000/api/v1`)

Interactive docs are also auto-generated at `/docs` (Swagger UI) and
`/redoc` whenever the server is running — every endpoint below is
directly testable from there.

## Authentication

Every endpoint except `/auth/*`, `/health`, and `GET /gold-rate` requires:

```
Authorization: Bearer <supabase-access-token>
```

The token is obtained by the Flutter app directly from Supabase Auth
(email/password, Google OAuth, or anonymous guest sign-in) — this backend
only verifies it, using `SUPABASE_JWT_SECRET`. Google sign-in and guest
sessions are never proxied through this API; they simply arrive here
already authenticated, exactly like an email/password session.

### Role-based authorization

Every user has a `role` — `"user"` (default) or `"admin"` — stored in the
`users` table. Endpoints under `/admin/*` additionally require the
caller's role to be `"admin"`, checked against the database (never
trusted from the JWT itself, since Supabase tokens don't carry
app-specific roles). Non-admins get `403 forbidden`. See
`supabase/schema.sql` §4 for how to bootstrap your first admin.

## Error format

Every error response (from any endpoint) has this shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Stone weight cannot exceed gross weight.",
    "details": {}
  }
}
```

| HTTP status | `code` | Meaning |
|---|---|---|
| 401 | `unauthorized` | Missing/invalid/expired token |
| 403 | `forbidden` | Valid token, but not allowed to access this resource (includes non-admin calling an admin endpoint) |
| 404 | `not_found` | Resource doesn't exist |
| 409 | `conflict` | Data conflict (e.g. duplicate) |
| 422 | `validation_error` | Request body/query failed validation |
| 429 | Handled by slowapi | Rate limit exceeded |
| 502 | `upstream_service_error` | Supabase Auth or the gold rate provider failed |
| 500 | `internal_error` / `database_error` | Unexpected server error (includes a reference ID for log lookup) |

---

## Authentication

### `POST /auth/signup`

Rate limit: 10/minute.

Request:
```json
{ "email": "jane@example.com", "password": "correcthorse123", "name": "Jane" }
```

Response `201`:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": { "id": "uuid", "email": "jane@example.com", "is_anonymous": false, "role": "user" }
}
```

### `POST /auth/login`

Rate limit: 10/minute. Same response shape as signup.

### `POST /auth/logout`

Request: `{ "access_token": "..." }` → `200 { "message": "Signed out successfully." }`

---

## Gold Rate

### `GET /gold-rate`

No authentication required. Rate limit: 60/minute.

Response `200`:
```json
{
  "rate_24k": 7420.50,
  "rate_22k": 6797.18,
  "rate_20k": 6182.28,
  "rate_18k": 5565.38,
  "source": "goldapi",
  "updated_at": "2026-07-11T09:00:00Z",
  "is_stale": false
}
```

`is_stale: true` means the cached rate is older than
`GOLD_RATE_REFRESH_INTERVAL_MINUTES` and the live provider could not be
reached — the app should show an "offline / last known rate" indicator.
If this happens on a completely empty database (first-ever boot) *and*
the provider is down, the response instead falls back to
`GOLD_RATE_FALLBACK_24K` from server config, with `source: "static_fallback"`
and `is_stale: true`.

---

## Gold Value Calculator

### `POST /calculate`

Auth required. Rate limit: 30/minute. **Stateless — nothing is saved.**

Request:
```json
{
  "gross_weight": 20,
  "stone_weight": 2,
  "purity": 0.916,
  "gold_rate": 6000,
  "ltv_percent": 75,
  "wastage_percent": 2,
  "making_charges_percent": 8,
  "gst_percent": 3
}
```

Validation:
- `gross_weight > 0`, `stone_weight >= 0`, `stone_weight <= gross_weight`
- `0 < purity <= 1` (e.g. 22K = `0.916`)
- `gold_rate > 0`
- `0 < ltv_percent <= 100` (defaults to `75`)
- `wastage_percent`, `making_charges_percent`, `gst_percent` — each `0-100`, all default to `0`

Response `200`:
```json
{
  "net_weight": 18.0,
  "effective_weight": 18.36,
  "pure_gold_weight": 16.818,
  "gold_value": 100908.0,
  "making_charges_amount": 8072.64,
  "gst_amount": 3269.42,
  "final_value": 112250.06,
  "loan_amount": 75681.0
}
```

**Calculation order** (SOP requirement #3):
`net_weight = gross − stone` → `effective_weight = net_weight × (1 + wastage%)`
→ `pure_gold_weight = effective_weight × purity` → `gold_value = pure_gold_weight × rate`
→ `making_charges_amount = gold_value × making_charges%` → `gst_amount = (gold_value + making_charges_amount) × gst%`
→ `final_value = gold_value + making_charges_amount + gst_amount`.

**`loan_amount` is always `gold_value × ltv%`** — never `final_value × ltv%`.
A gold loan is collateralized against the metal itself; making charges and
GST are retail pricing with no resale value, so they're deliberately
excluded from the loan basis (matches real-world lender practice).

---

## Gold Loan Estimator

### `POST /loan/estimate`

Auth required. Rate limit: 30/minute. Stateless.

Request — supply **either** `gold_value` **or** `calculation_id`, not both:
```json
{
  "gold_value": 100000,
  "ltv_percent": 75,
  "annual_interest_rate_percent": 12,
  "tenure_months": 12
}
```
or
```json
{
  "calculation_id": "uuid-of-a-saved-calculation",
  "ltv_percent": 75,
  "annual_interest_rate_percent": 12,
  "tenure_months": 12
}
```

Response `200`:
```json
{
  "gold_value": 100000.0,
  "eligible_loan_amount": 75000.0,
  "ltv_percent": 75.0,
  "annual_interest_rate_percent": 12.0,
  "tenure_months": 12,
  "monthly_emi": 6663.66,
  "total_interest": 4963.92,
  "total_repayment": 79963.92
}
```

EMI uses the standard reducing-balance formula. A `0%` interest rate
splits the principal evenly across the tenure instead of dividing by zero.

---

## History

### `GET /history`

Auth required. Rate limit: 60/minute.

Query params: `page` (default 1), `page_size` (default 20, max 100),
`search` (matches ornament name, case-insensitive), `sort_by` — one of
`newest` (default) | `oldest` | `highest_value` | `lowest_value`,
`date_from` / `date_to` (ISO 8601, inclusive — new filter).

Response `200`:
```json
{
  "items": [
    {
      "id": "uuid",
      "ornament_name": "Necklace",
      "gross_weight": 20.0,
      "stone_weight": 2.0,
      "purity": 0.916,
      "gold_rate": 6000.0,
      "ltv_percent": 75.0,
      "wastage_percent": 2.0,
      "making_charges_percent": 8.0,
      "gst_percent": 3.0,
      "pure_gold_weight": 16.818,
      "gold_value": 100908.0,
      "making_charges_amount": 8072.64,
      "gst_amount": 3269.42,
      "final_value": 112250.06,
      "loan_amount": 75681.0,
      "created_at": "2026-07-11T09:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "has_next": false
}
```

### `GET /history/export`

Auth required. Rate limit: 10/minute. Same `search`/`date_from`/`date_to`
filters as above (no pagination — capped at 5000 rows). Returns a
`text/csv` file download (`Content-Disposition: attachment`) — SOP §7
"Export support".

### `POST /history`

Auth required. Rate limit: 30/minute. Same body as `/calculate` plus
`ornament_name` (required, 1–255 chars). Persists the calculation and
returns the saved row (`201`, same shape as an item above).

### `PUT /history/{calculation_id}`

Auth required. Rate limit: 30/minute. All fields optional — only supplied
fields are updated; derived figures (`pure_gold_weight`, `gold_value`,
`making_charges_amount`, `gst_amount`, `final_value`, `loan_amount`) are
automatically recomputed using the record's **existing** values for any
field you don't supply (fixed bug: earlier builds incorrectly reset
`ltv_percent` to a hardcoded 75% whenever it wasn't included in the
update — this is now correctly preserved). Returns `404` if not found,
`403` if it belongs to another user.

### `DELETE /history/{calculation_id}`

Auth required. Rate limit: 30/minute. Returns `204` on success.

---

## Settings

### `GET /settings`

Auth required. Rate limit: 60/minute. Auto-creates a default settings row
on first call for a new user.

Response `200`:
```json
{
  "default_ltv": 75.0,
  "default_purity": "22K",
  "currency": "INR",
  "auto_rate": true,
  "theme": "system",
  "default_wastage_percent": 0.0,
  "default_making_charges_percent": 0.0,
  "default_gst_percent": 3.0,
  "notifications_enabled": true
}
```

### `PUT /settings`

Auth required. Rate limit: 30/minute. All fields optional (partial
update). `default_purity` must be one of `18K|20K|22K|24K`; `theme` one of
`light|dark|system`.

---

## Dashboard

### `GET /dashboard/summary`

Auth required. Rate limit: 60/minute. Aggregates everything a Home/Dashboard
screen needs in one call (SOP requirement #5):

```json
{
  "gold_rate": { "rate_24k": 7420.50, "...": "...", "is_stale": false },
  "market_status": "live",
  "recent_calculations": [ "...up to 5 most recent CalculationResponse objects..." ],
  "stats": { "total_calculations": 12, "total_gold_value_calculated": 845200.50 }
}
```

`market_status` is `"live"` when the served gold rate is fresh, `"delayed"`
when it's a stale/fallback rate — the honest, directly-derivable signal
available (a true bullion-market-hours calendar is out of scope).

---

## Reports

### `GET /reports/calculations/{calculation_id}/pdf`

Auth required. Rate limit: 20/minute. Downloads a professional one-page
PDF report (`application/pdf`) for a saved calculation — SOP §8. Same
ownership check as History: `404` if not found, `403` if it belongs to
another user.

---

## Admin (role-based authorization required)

Every endpoint below requires the caller's `users.role` to be `"admin"` —
otherwise `403 forbidden`, regardless of whether the token itself is
valid.

### `GET /admin/stats`

Rate limit: 30/minute. Platform-wide aggregate stats:
```json
{ "total_users": 128, "total_calculations": 940, "total_gold_value_calculated": 58200000.0 }
```

### `PUT /admin/users/{user_id}/role`

Rate limit: 10/minute. Body: `{ "role": "admin" }` or `{ "role": "user" }`.
The only way a user ever becomes an admin via the API — there is no
self-service endpoint (see `supabase/schema.sql` §4 for bootstrapping the
very first admin via direct SQL).

### `POST /admin/gold-rate/refresh`

Rate limit: 10/minute. Manually triggers an immediate live gold-rate
refresh, bypassing the hourly scheduler — useful right after a known
provider outage.

---

## `GET /health`

No auth. Returns `{ "status": "ok", "env": "production" }`. Used by
container/load-balancer health checks.
