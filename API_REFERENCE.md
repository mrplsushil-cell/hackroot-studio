# API Reference — Hackroot Studio

Base URL (prod): `https://api.hackroot.studio/api/v1`
Auth: `Authorization: Bearer <JWT>` for user endpoints; `Authorization: Bearer <api_key>` for public API.
All timestamps UTC (ISO-8601). Amounts in minor units (paise for INR).

---

## Auth
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/auth/register` | — | body `{email,password,full_name}` → 201 + token |
| POST | `/auth/login` | — | → 200 + token |
| GET | `/auth/me` | user | current user |
| POST | `/auth/password-reset/request` | — | 202 always (no enum) |
| POST | `/auth/password-reset/confirm` | — | body `{token,password}` → 200 |

## Videos / Library
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/videos` | user | list |
| POST | `/videos` | user | create |
| GET | `/videos/{id}` | user | detail (output_path, thumbnail_path, resolution) |
| DELETE | `/videos/{id}` | user | delete |
| PATCH | `/videos/{id}/rename` | user | |
| POST | `/videos/{id}/duplicate` | user | |
| POST | `/videos/{id}/generate` | user | 202; enforces credits + plan limit |
| GET | `/videos/{id}/status` | user | job status |
| GET | `/videos/{id}/thumbnail` | user | image |
| GET | `/videos/{id}/download` | user | mp4 |

## Billing / Subscriptions
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/billing/plans` | user | 4 plans |
| GET | `/billing/current` | user | plan, subscription, credits_remaining/used |
| POST | `/billing/checkout` | user | `{plan_slug,billing_cycle}` → order (mock when no Razorpay keys) |
| POST | `/billing/verify` | user | `{razorpay_*,plan_slug,cycle}` → activates sub, grants credits, invoice |
| POST | `/billing/cancel` | user | cancel at period end |
| POST | `/billing/renew` | user | renew |
| POST | `/billing/change` | user | `?plan_slug=&billing_cycle=` |
| GET | `/billing/invoices` | user | list |
| GET | `/billing/credits/history` | user | ledger |
| GET | `/billing/notifications` | user | list |
| GET | `/billing/notifications/unread-count` | user | `{unread}` |
| POST | `/billing/notifications/{id}/read` | user | |
| POST | `/billing/notifications/read-all` | user | |
| POST | `/billing/webhook` | Razorpay sig | payment webhook |

## Team (Business)
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/team/members` | business | list |
| POST | `/team/invite` | business | `?email=&role=` |
| DELETE | `/team/members/{id}` | business | remove |

## Brand Kit / Templates / Assets / Agents
- `GET/POST /brand-kit`, `POST /brand-kit/{id}/logo`, `POST /brand-kit/{id}/default`
- `GET/POST /templates`
- `GET /assets`, `POST /assets/upload`
- `GET /agents` (9 agents)

## Admin (superuser)
`/admin/stats`, `/admin/users`, `/admin/users/{id}/credits?amount=`, `/admin/subscriptions`,
`/admin/plans`, `/admin/invoices`, `/admin/templates`, `/admin/brand-kits`, `/admin/videos`,
`/admin/logs/requests`, `/admin/audit-logs`, `/admin/analytics`.

## Public API (Business, API key)
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api-keys` | user | create key (full key returned once) |
| GET | `/api-keys` | user | list |
| POST | `/api/v1/generate-video` | api key | body `{prompt,duration,...}` → video_id + cost |
| POST | `/api/v1/script` | api key | → script text |
| POST | `/api/v1/thumbnail` | api key | → thumbnail URL |
Quota enforced per key (429 when `usage_count >= monthly_quota`).

## Settings
- `GET /settings` — client-safe config + **provider status** (no secrets).

## Credit formula
`10s=1, 20s=2, 30s=3, 60s=5, then 5 credits per 30s block.`

---

## Responses & Errors

All success responses are JSON. The error envelope is:

```json
{ "detail": "Human-readable message" }
```

or (validation) a list:

```json
{ "detail": [ { "loc": ["body","email"], "msg": "value is not a valid email", "type": "value_error" } ] }
```

### Standard status codes
| Code | Meaning | Typical trigger |
|---|---|---|
| 200 | OK | successful GET / action |
| 201 | Created | register, create video/key/asset/template |
| 202 | Accepted | async job enqueued (`/videos/{id}/generate`, public `/generate-video`) |
| 400 | Bad Request | invalid reset token, bad Razorpay signature (prod) |
| 401 | Unauthorized | missing/invalid/expired JWT or API key |
| 402 | Payment Required | insufficient credits on generate |
| 403 | Forbidden | non-superuser hitting admin route |
| 404 | Not Found | object not owned by caller / does not exist |
| 413 | Payload Too Large | upload exceeds size cap |
| 415 | Unsupported Media Type | bad upload extension/MIME |
| 422 | Unprocessable Entity | Pydantic validation failure (bad input shape) |
| 429 | Too Many Requests | rate limit / API-key quota exceeded |

---

## Examples

### Register + authenticate
```bash
curl -X POST https://api.hackroot.studio/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@acme.com","password":"Str0ng!Pass","full_name":"You"}'
# → 201 { "access_token": "eyJ...", "token_type": "bearer", "user": {...} }

curl -X POST https://api.hackroot.studio/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@acme.com","password":"Str0ng!Pass"}'
# → 200 { "access_token": "eyJ..." }
```

### Create + generate a video (Bearer JWT)
```bash
VID=$(curl -X POST https://api.hackroot.studio/api/v1/videos \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"prompt":"A cinematic product reveal","duration":20,"aspect_ratio":"9:16"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["id"])')

curl -X POST https://api.hackroot.studio/api/v1/videos/$VID/generate \
  -H "Authorization: Bearer $TOKEN"
# → 202 { "job_id": ..., "status": "queued", "cost_credits": 2 }
```

### Public API (API key)
```bash
curl -X POST https://api.hackroot.studio/api/v1/generate-video \
  -H "Authorization: Bearer $API_KEY" -H 'Content-Type: application/json' \
  -d '{"prompt":"Launch teaser","duration":10}'
# → 202 { "video_id": ..., "cost_credits": 1 }
```

### Download
```bash
curl -L https://api.hackroot.studio/api/v1/videos/$VID/download \
  -H "Authorization: Bearer $TOKEN" -o video.mp4
# → 200 video/mp4
```

### Billing — current plan + credits
```bash
curl https://api.hackroot.studio/api/v1/billing/current \
  -H "Authorization: Bearer $TOKEN"
# → 200 { "plan": {"slug":"free"}, "credits_remaining": 98, "credits_used": 2 }
```
