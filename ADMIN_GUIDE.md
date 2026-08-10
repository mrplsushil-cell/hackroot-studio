# Hackroot Studio — Administrator Guide

**Release:** RC-8 (production)
**Audience:** operators / owners running a Hackroot Studio deployment
**Scope:** everything reachable through the admin API (`/api/v1/admin/*`) plus the
operational tasks that live outside the app (bootstrapping the first admin,
provider configuration, monitoring, backup and restore).

Everything documented here was verified against the code in
`backend/app/api/v1/admin.py`, `backend/app/models/`, and
`backend/app/services/`. No endpoint or field is listed that does not exist.

---

## 1. Admin access model

There is **no seeded, auto-created administrator account.** A fresh deployment
contains only the users who sign up through the normal registration flow, and
every one of them is created with `is_superuser = false`
(`backend/app/models/user.py`). The first admin must be promoted by hand,
directly in the database.

Authorization itself is deliberately simple: every route in the admin router
calls `_require_admin()`, which raises **403 `Admin access required`** unless the
authenticated user's `is_superuser` flag is true. There are no roles, scopes or
per-endpoint permissions beyond that single boolean.

### 1.1 Promoting the first administrator

Register the account normally through the UI or `POST /api/v1/auth/register`,
then flip the flag in PostgreSQL:

```bash
# Docker Compose deployment
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U hackroot -d hackroot -c \
  "UPDATE users SET is_superuser = true WHERE email = 'owner@example.com';"
```

Verify the change before relying on it:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U hackroot -d hackroot -c \
  "SELECT id, email, is_active, is_superuser FROM users WHERE is_superuser;"
```

To revoke admin rights, run the same statement with `is_superuser = false`.
To suspend a user entirely, set `is_active = false` — the login flow rejects
inactive accounts.

> **Operational note.** Promotion via SQL is intentionally the only path: there
> is no API endpoint that grants superuser, so an attacker who compromises an
> admin token still cannot mint new administrators through the API.

### 1.2 Obtaining an admin token

All admin calls are ordinary JWT-authenticated requests. Log in as the promoted
user and reuse the access token as a Bearer credential:

```bash
BASE=https://your-host/api/v1

TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@example.com","password":"••••••••"}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

echo "$TOKEN"
```

Every example below assumes `$BASE` and `$TOKEN` are set. Token lifetime is
governed by `JWT_EXPIRES_MINUTES` (visible via `GET /settings`).

---

## 2. Dashboard statistics — `GET /admin/stats`

The single call that powers the owner dashboard. All figures are computed live
against the database; the "last 30 days" windows are rolling, measured back from
the moment of the request.

```bash
curl -s "$BASE/admin/stats" -H "Authorization: Bearer $TOKEN"
```

| Field | Meaning |
|---|---|
| `total_users` | Count of all rows in `users`. |
| `active_subscriptions` | Subscriptions whose `status = 'active'`. |
| `total_videos` | All videos ever created. |
| `videos_last_30d` | Videos created in the rolling 30-day window. |
| `revenue_last_30d` | Sum of `invoices.total_amount` for **paid** invoices in the window, in **minor units** (paise/cents). |
| `new_users_last_30d` | Signups in the window. |
| `credits_consumed` | Absolute sum of all negative ledger entries (lifetime, not windowed). |
| `failed_payments` | Invoices with `status = 'failed'`. |

Currency amounts are integers in minor units throughout the system — a
`revenue_last_30d` of `499000` means ₹4,990.00 when the plan currency is INR.

---

## 3. User management

### 3.1 Listing and searching users — `GET /admin/users`

Returns the most recently created users first.

Query parameters:

- `limit` — 1–500, default **100**
- `q` — optional case-insensitive substring match on email

```bash
# Newest 50 users
curl -s "$BASE/admin/users?limit=50" -H "Authorization: Bearer $TOKEN"

# Find a specific customer
curl -s "$BASE/admin/users?q=acme.com" -H "Authorization: Bearer $TOKEN"
```

Each record contains: `id`, `email`, `full_name`, `is_active`, `is_superuser`,
`credits_total`, `credits_used`, `created_at`.

A user's *remaining* balance is `credits_total - credits_used` (never negative —
the service clamps it at zero).

There is no admin endpoint to edit or delete a user. Deactivation, renaming and
promotion are database operations (see §1.1).

### 3.2 Adjusting credits — `POST /admin/users/{uid}/credits`

The one mutating action on a user account exposed over the API. `amount` is a
**query parameter**, not a JSON body, and it may be negative to claw credits
back. An optional `note` is stored on the ledger entry.

```bash
# Grant 500 credits with a reason
curl -s -X POST "$BASE/admin/users/42/credits?amount=500&note=goodwill%20credit" \
  -H "Authorization: Bearer $TOKEN"

# Deduct 100 credits
curl -s -X POST "$BASE/admin/users/42/credits?amount=-100&note=refund%20reversal" \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```json
{"user_id": 42, "credits_total": 1500, "credits_used": 240}
```

What happens behind the call (`app/services/credits.grant_credits`):

1. The user row is locked with `SELECT … FOR UPDATE`, so concurrent grants and
   generation-time deductions cannot race.
2. `credits_total` becomes `max(0, credits_total + amount)`. **The total is
   clamped at zero** — a large negative adjustment floors the balance rather
   than producing a negative total that would corrupt the remaining-credits
   arithmetic. If you send `amount=-99999` against a user with 300 credits, the
   total lands on 0, and the ledger records the raw `change` you submitted.
3. An append-only `credit_transactions` row is written with
   `reason = "admin_grant"`, `admin_user_id` set to *your* user id, and your
   `note`.
4. An `audit_logs` row is written: `action = "adjust_credits"`,
   `target_type = "user"`, `target_id = <uid>`, `detail = "amount=<n>"`.

Unknown user id returns **404 `User not found`**.

---

## 4. Billing oversight

### 4.1 Subscriptions — `GET /admin/subscriptions`

```bash
curl -s "$BASE/admin/subscriptions?limit=100" -H "Authorization: Bearer $TOKEN"
```

Newest first; `limit` 1–500 (default 100). Fields: `id`, `user_id`, `plan`
(plan display name, or `null` if the plan row is missing), `status`,
`billing_cycle`, `current_period_end`.

Status values used by the model: `active`, `trialing`, `past_due`, `cancelled`,
`expired`. Only `active` counts toward `active_subscriptions` in `/admin/stats`.

### 4.2 Plans — `GET /admin/plans` and `PATCH /admin/plans/{pid}`

```bash
curl -s "$BASE/admin/plans" -H "Authorization: Bearer $TOKEN"
```

Returns every plan (including inactive ones) ordered by `sort_order`. Plan rows
carry `slug`, `name`, `price_monthly`, `price_yearly`, `currency`,
`credits_per_month`, `video_limit` (0 = unlimited), `has_watermark`,
`priority_queue`, `api_access`, `team_members`, `is_active`,
`razorpay_plan_id`.

Retiring or re-enabling a plan is the only plan mutation available:

```bash
# Hide a plan from the pricing page
curl -s -X PATCH "$BASE/admin/plans/3?is_active=false" \
  -H "Authorization: Bearer $TOKEN"
```

Response: `{"id": 3, "is_active": false}`. Pricing, credit allowances and
feature flags are **not** editable through the API — change them in the
database or through the plan seed data and restart. Deactivating a plan does not
cancel existing subscriptions to it.

### 4.3 Invoices — `GET /admin/invoices`

```bash
curl -s "$BASE/admin/invoices?limit=200" -H "Authorization: Bearer $TOKEN"
```

Newest first. Fields: `id`, `invoice_no`, `user_id`, `amount` (this is the
invoice's `total_amount`, i.e. inclusive of tax), `currency`, `status`,
`created_at`.

Invoice statuses: `draft`, `pending`, `paid`, `failed`, `refunded`, `void`.
Only `paid` invoices feed revenue metrics; `failed` feeds `failed_payments`.
Razorpay correlation ids (`razorpay_order_id`, `razorpay_payment_id`) exist on
the model but are not returned by the admin list — query the `invoices` table
directly when reconciling with the payment gateway.

---

## 5. Credits and the ledger

Credits are the metering unit for generation. Two numbers live on the user row:
`credits_total` (entitlement) and `credits_used` (consumed). Every change is
mirrored into the append-only `credit_transactions` ledger, which is the
authoritative audit trail.

Ledger `reason` values written by the system:

| Reason | Written when |
|---|---|
| `consume` | A generation deducts credits (`change` negative). |
| `admin_grant` | An admin uses `POST /admin/users/{id}/credits`. |
| `monthly_reset` | The monthly allowance resets: `credits_total = plan.credits_per_month`, `credits_used = 0`. |
| `bonus`, `signup`, `refund`, `purchase` | Other grant paths through `grant_credits`. |

Ledger row fields: `change`, `balance_after`, `reason`, `reference_type`,
`reference_id`, `admin_user_id`, `note`, `created_at`.

### 5.1 Reading a ledger — `GET /billing/credits/history`

Important: this endpoint is **user-scoped, not admin-scoped**. It returns the
transactions of the *calling* account only, so an admin token shows the admin's
own ledger.

```bash
curl -s "$BASE/billing/credits/history?limit=50" -H "Authorization: Bearer $TOKEN"
```

`limit` is 1–200, default 50, newest first.

To inspect *another* user's ledger, query the database:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U hackroot -d hackroot -c \
  "SELECT created_at, change, balance_after, reason, admin_user_id, note
     FROM credit_transactions WHERE user_id = 42
     ORDER BY created_at DESC LIMIT 50;"
```

Never adjust `credits_total` or `credits_used` with raw SQL. Doing so bypasses
the ledger and the row lock, leaving the audit trail permanently out of sync
with the balance. Use the admin endpoint.

---

## 6. Content overview

Three read-only inventory endpoints, each accepting `limit` (1–500):

```bash
curl -s "$BASE/admin/templates"   -H "Authorization: Bearer $TOKEN"
curl -s "$BASE/admin/brand-kits"  -H "Authorization: Bearer $TOKEN"
curl -s "$BASE/admin/videos?limit=200" -H "Authorization: Bearer $TOKEN"
```

- **Templates** — `id`, `name`, `category`, `is_system`, `is_active`.
- **Brand kits** — `id`, `name`, `owner_id`, `is_default`.
- **Videos** — `id`, `owner_id`, `title`, `duration`, `status`, `created_at`;
  newest first. Use this to spot jobs stuck in a non-terminal status.

---

## 7. Logs and audit trail

### 7.1 Request logs — `GET /admin/logs/requests`

The security/traffic view. `limit` 1–500, default **200**, newest first.

```bash
curl -s "$BASE/admin/logs/requests?limit=200" -H "Authorization: Bearer $TOKEN"
```

Returned fields: `id`, `method`, `path`, `status_code`, `user_id`, `ip`,
`created_at`. The underlying `request_logs` table also stores `api_key_id` and
`latency_ms`, which are available via SQL if you need latency analysis:

```sql
SELECT path, count(*), avg(latency_ms)::int
FROM request_logs
WHERE created_at > now() - interval '1 hour'
GROUP BY path ORDER BY 2 DESC LIMIT 20;
```

Typical uses: spotting credential-stuffing bursts against `/auth/login`
(repeated 401s from one `ip`), and finding 5xx clusters after a deploy.

### 7.2 Audit logs — `GET /admin/audit-logs`

The privileged-action trail. `limit` 1–500, default **200**, newest first.

```bash
curl -s "$BASE/admin/audit-logs?limit=100" -H "Authorization: Bearer $TOKEN"
```

Returned fields: `id`, `actor_id`, `action`, `target_type`, `detail`,
`created_at`. The table additionally holds `actor_type` (`user` | `system` |
`admin`) and `target_id`.

Credit adjustments are the action guaranteed to appear here
(`action = "adjust_credits"`, `detail = "amount=…"`). Review this log whenever
a balance discrepancy is reported — cross-reference `actor_id` against
`credit_transactions.admin_user_id` for the same user and timestamp.

Both log tables grow without bound; see §10.4 for retention.

### 7.3 Analytics — `GET /admin/analytics`

```bash
curl -s "$BASE/admin/analytics" -H "Authorization: Bearer $TOKEN"
```

Returns:

- `daily_revenue` — 14 entries, oldest to newest, each `{date, revenue}`. Only
  **paid** invoices count; revenue is in minor units.
- `top_plans` — `{name, count}` per plan, counting active subscriptions.
- `top_templates` — top 5 templates by number of videos referencing them.
- `top_users` — top 5 users by video count, keyed by `email`.
- `active_users` — count of distinct video owners (lifetime, not windowed).

This endpoint runs 14 sequential aggregate queries plus three joins. It is safe
for a dashboard refresh but should not be polled aggressively.

---

## 8. Provider configuration

Hackroot Studio talks to external LLM, image, video, music, TTS, payment and
email providers. Each defaults to `mock`, which produces placeholder output —
a deployment left on defaults will run end to end but generate nothing real.

### 8.1 Checking provider status — `GET /settings`

`/settings` is read-only and never returns secrets; it reports which provider is
selected for each capability so a missing credential shows up as a status
rather than a silent failure.

```bash
curl -s "$BASE/settings" -H "Authorization: Bearer $TOKEN"
```

The `providers` block reports `llm`, `image`, `video`, `music`, `tts`,
`payments` (`"razorpay"` when `RAZORPAY_KEY_ID` is set, otherwise `"mock"`) and
`email`. The response also exposes storage settings (backend, local root,
public base URL, max upload size), rendering defaults (ffmpeg/ffprobe paths,
preset, CRF, audio codec and bitrate) and the JWT algorithm and expiry.

**Post-deploy check:** call `/settings` and confirm no capability you rely on
still reads `mock`.

### 8.2 Configuring providers

Providers are configured exclusively through environment variables, loaded at
process start. Start from `production.env.example`, then restart the `backend`
and `worker` containers — there is no hot reload.

| Capability | Selector | Credential |
|---|---|---|
| LLM / scripting | `LLM_PROVIDER` | `LLM_API_KEY` |
| Image generation | `IMAGE_PROVIDER` | `IMAGE_API_KEY` |
| Video generation | `VIDEO_PROVIDER` | `VIDEO_API_KEY` |
| Text-to-speech | `TTS_PROVIDER` | `TTS_API_KEY` |
| Music | `MUSIC_PROVIDER` | `MUSIC_API_KEY` |
| Payments | `PAYMENT_PROVIDER` (default `razorpay`) | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` |
| Email | `EMAIL_PROVIDER` (`mock` \| `smtp`) | SMTP settings in `production.env` |

Core infrastructure variables live alongside them: `DATABASE_URL`, `REDIS_URL`,
`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, plus the JWT secret.

```bash
vi production.env          # edit selectors and keys
docker compose -f docker-compose.prod.yml up -d backend worker
curl -s "$BASE/settings" -H "Authorization: Bearer $TOKEN"   # confirm
```

Rotating a payment key requires updating the webhook secret in the Razorpay
dashboard at the same time, or inbound webhooks will start failing signature
verification and invoices will stall in `pending`.

---

## 9. Monitoring

### 9.1 Application health

The backend exposes an unauthenticated liveness endpoint:

```bash
curl -s https://your-host/health
```

### 9.2 Container health

The production compose file defines healthchecks for `postgres`
(`pg_isready`), `redis` (`redis-cli ping`), `backend` (`curl -f
localhost:8000/health`, every 30s) and `frontend` (`wget -qO- localhost:3000/`,
every 30s). Services: `postgres`, `redis`, `backend`, `worker`, `frontend`,
`nginx`.

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f --tail=100 backend
docker compose -f docker-compose.prod.yml logs -f --tail=100 worker
```

Note that the `worker` service has no healthcheck — it must be monitored via
queue depth and logs.

### 9.3 Celery queue

Video generation runs asynchronously on the Celery worker with Redis as broker
(`CELERY_BROKER_URL`, default database 1) and result backend (database 2).

```bash
# Live worker view: active, scheduled and reserved tasks
docker compose -f docker-compose.prod.yml exec worker celery -A app.worker inspect active
docker compose -f docker-compose.prod.yml exec worker celery -A app.worker inspect reserved
docker compose -f docker-compose.prod.yml exec worker celery -A app.worker status

# Broker backlog (queue length in the broker DB)
docker compose -f docker-compose.prod.yml exec redis redis-cli -n 1 llen celery
```

A backlog that grows while `inspect active` stays empty means the worker is
down or disconnected — restart it with
`docker compose -f docker-compose.prod.yml restart worker`.

Cross-check against the application's own view: videos sitting in a
non-terminal `status` in `GET /admin/videos` while the queue is empty indicate
jobs that died mid-flight. Per-step detail for a failed job is recorded in the
`generation_logs` table (`job_id`, `level`, `step`, `message`, `detail`).

### 9.4 Redis and Postgres

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli info memory
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U hackroot -d hackroot -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## 10. Backup and restore

Authoritative, step-by-step procedures live in **`docs/BACKUP_RESTORE.md`**;
deployment-level context is in `DEPLOYMENT_GUIDE.md` and `docs/deployment.md`.
This section is the operator's quick reference.

Three things must be backed up together to get a consistent restore:

1. **PostgreSQL** — users, credits, subscriptions, invoices, videos, logs.
2. **Storage volume** — rendered videos and uploaded assets (`storage_data`).
3. **`production.env`** — secrets and provider keys, stored separately from the
   database dump and never in version control.

### 10.1 Database backup (`pg_dump`)

```bash
STAMP=$(date +%Y%m%d-%H%M%S)

docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U hackroot -d hackroot --format=custom --no-owner \
  > "hackroot-${STAMP}.dump"

# Verify the dump is readable before trusting it
pg_restore --list "hackroot-${STAMP}.dump" | head
```

The custom format is compressed and supports selective restore. Use
`--format=plain` if you need a human-readable SQL file.

### 10.2 Storage backup

```bash
docker run --rm \
  -v hackroot_storage_data:/data:ro \
  -v "$PWD":/backup alpine \
  tar czf "/backup/storage-${STAMP}.tar.gz" -C /data .
```

(Adjust the volume name to match `docker volume ls` output for your project.)

### 10.3 Restore

Restoring is destructive. Stop the application tier first so nothing writes
mid-restore, and keep `postgres` running:

```bash
docker compose -f docker-compose.prod.yml stop backend worker frontend

docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U hackroot -d postgres -c \
  "DROP DATABASE hackroot; CREATE DATABASE hackroot OWNER hackroot;"

docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U hackroot -d hackroot --no-owner < "hackroot-${STAMP}.dump"

docker compose -f docker-compose.prod.yml up -d backend worker frontend
```

After the stack is back up:

- `curl -s https://your-host/health`
- `curl -s "$BASE/admin/stats" -H "Authorization: Bearer $TOKEN"` and compare
  `total_users` / `total_videos` against pre-restore figures
- confirm your admin account still has `is_superuser = true` — if you restored a
  dump taken before the promotion, re-run the SQL in §1.1
- confirm `/settings` shows the expected providers (these come from the
  environment, not the dump)

Rehearse the restore on a staging copy at least once per release cycle. A dump
that has never been restored is not a backup.

### 10.4 Log retention

`request_logs` and `audit_logs` grow with traffic and are never pruned by the
application. Trim `request_logs` on a schedule to keep dump size and query times
sane; **keep `audit_logs` far longer** — it is the record of privileged actions.

```sql
DELETE FROM request_logs WHERE created_at < now() - interval '90 days';
```

---

## 11. Admin endpoint reference

All paths are relative to `/api/v1`. Every route requires a Bearer token
belonging to a user with `is_superuser = true`; anything else returns
403 `Admin access required`.

| Method | Path | Parameters | Purpose |
|---|---|---|---|
| GET | `/admin/stats` | — | Dashboard KPIs |
| GET | `/admin/users` | `limit` (1–500, def 100), `q` | List / search users |
| POST | `/admin/users/{uid}/credits` | `amount` (required, may be negative), `note` | Adjust credits; audited |
| GET | `/admin/subscriptions` | `limit` (def 100) | Subscriptions, newest first |
| GET | `/admin/plans` | — | All plans by `sort_order` |
| PATCH | `/admin/plans/{pid}` | `is_active` | Enable / disable a plan |
| GET | `/admin/invoices` | `limit` (def 100) | Invoices, newest first |
| GET | `/admin/templates` | `limit` (def 100) | Template inventory |
| GET | `/admin/brand-kits` | `limit` (def 100) | Brand kit inventory |
| GET | `/admin/videos` | `limit` (def 100) | Videos, newest first |
| GET | `/admin/logs/requests` | `limit` (1–500, def 200) | HTTP request log |
| GET | `/admin/audit-logs` | `limit` (1–500, def 200) | Privileged-action trail |
| GET | `/admin/analytics` | — | 14-day revenue, top plans/templates/users |

Related non-admin endpoints referenced above: `GET /settings` (provider and
config status), `GET /billing/credits/history` (caller's own ledger),
`GET /health` (liveness, unauthenticated).

---

## 12. Operator checklist

**On first deploy**

- [ ] Register the owner account, then promote it with SQL (§1.1)
- [ ] Confirm `GET /settings` shows no unwanted `mock` providers (§8.1)
- [ ] Confirm all compose services are healthy (§9.2)
- [ ] Take and verify a first `pg_dump` (§10.1)

**Daily / weekly**

- [ ] `GET /admin/stats` — watch `failed_payments` and signup trend
- [ ] `GET /admin/audit-logs` — review credit adjustments
- [ ] Celery backlog vs. active tasks (§9.3)
- [ ] Backups completing and restorable

**Per release**

- [ ] Rehearse a restore on staging (§10.3)
- [ ] Prune `request_logs` (§10.4)
