# ENVIRONMENT — Configuration Reference

Every variable read by the backend is declared in `backend/app/config.py`
(`pydantic-settings`, `case_sensitive=False`, `env_file=".env"`,
`extra="ignore"`). Environment variables always win over `.env`.

> **`extra="ignore"` warning.** Unknown keys are silently dropped — a typo, or a
> legacy name from `production.env.example`, will not raise an error; the
> default is used instead. Cross-check against the tables below.

Legend for **Prod**: ✅ set explicitly · ⚠️ set if you use the feature ·
➖ default is fine.

---

## Core

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `APP_NAME` | Display name (health/root payloads, emails) | `Hackroot Studio` | ➖ |
| `APP_ENV` | `development` \| `production`. Gates dev `init_db()`, and enables the rate limiter + `RequestLog` audit middleware when `production` | `development` | ✅ `production` |
| `APP_DEBUG` | Returns raw exception text from the 500 handler when true | `true` | ✅ `false` |
| `APP_SECRET_KEY` | General app secret | `change-me` | ✅ 32-byte hex |
| `APP_BASE_URL` | Public backend base URL | `http://localhost:8000` | ✅ |
| `FRONTEND_BASE_URL` | Public frontend URL — **also the CORS allow-list entry** | `http://localhost:3000` | ✅ |

## Database

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `DATABASE_URL` | SQLAlchemy async DSN (`postgresql+asyncpg://…`) | `postgresql+asyncpg://hackroot:hackroot@localhost:5432/hackroot` | ✅ (compose builds it) |
| `POSTGRES_USER` | Postgres role — used by the `postgres` service and to compose `DATABASE_URL` | `hackroot` | ✅ |
| `POSTGRES_PASSWORD` | Postgres password | none (dev compose falls back to `hackroot`) | ✅ |
| `POSTGRES_DB` | Database name | `hackroot` | ✅ |
| `POSTGRES_HOST` / `POSTGRES_PORT` | Present in `.env.example` for convenience; **not read by config.py** — only `DATABASE_URL` is | `postgres` / `5432` | ➖ |

In `docker-compose.prod.yml` the backend and worker receive
`DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}`
as an explicit `environment:` entry, which overrides `production.env`.

## Redis / Celery

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `REDIS_URL` | General-purpose Redis connection (db 0) | `redis://localhost:6379/0` | ✅ `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Task broker (db 1) | `redis://localhost:6379/1` | ✅ (compose sets `redis://redis:6379/1`) |
| `CELERY_RESULT_BACKEND` | Result store (db 2) | `redis://localhost:6379/2` | ✅ (compose sets `redis://redis:6379/2`) |

Celery config (`app/jobs/celery_app.py`, not env-driven): JSON serializer, UTC,
`task_track_started`, `task_acks_late`, `worker_prefetch_multiplier=1`,
`task_default_queue="default"`.

## Storage

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `STORAGE_BACKEND` | `local` \| `s3` | `local` | ✅ |
| `STORAGE_LOCAL_ROOT` | Filesystem root for media; mounted from the `storage_data` volume and served at `/media` | `/data/storage` | ✅ |
| `STORAGE_PUBLIC_BASE_URL` | Public URL prefix for stored media | `http://localhost:8000/media` | ✅ |
| `S3_ENDPOINT` | S3-compatible endpoint | `None` | ⚠️ |
| `S3_REGION` | Bucket region | `None` | ⚠️ |
| `S3_BUCKET` | Bucket name | `None` | ⚠️ |
| `S3_ACCESS_KEY` | Access key | `None` | ⚠️ |
| `S3_SECRET_KEY` | Secret key | `None` | ⚠️ |

## JWT / Auth

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `JWT_SECRET` | HMAC signing key for access tokens | `change-me` | ✅ 32-byte hex, distinct from `APP_SECRET_KEY` |
| `JWT_ALGORITHM` | Signing algorithm | `HS256` | ➖ |
| `JWT_EXPIRES_MINUTES` | Token lifetime in minutes | `10080` (7 days) | ➖ / shorten if desired |

Passwords are bcrypt-hashed. Rotating `JWT_SECRET` invalidates every issued
token immediately.

## Providers — LLM

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `LLM_PROVIDER` | `mock` \| `openai` \| `anthropic` \| `google` | `mock` | ⚠️ |
| `LLM_API_KEY` | Key for the selected provider | `None` | ⚠️ required unless `mock` |
| `LLM_MODEL` | Model id | `gpt-4o-mini` | ⚠️ |
| `LLM_BASE_URL` | Override endpoint (proxies, self-hosted) | `None` | ⚠️ |

## Providers — Image

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `IMAGE_PROVIDER` | `mock` \| `openai` \| `stability` \| `replicate` | `mock` | ⚠️ |
| `IMAGE_API_KEY` | Provider key | `None` | ⚠️ |
| `IMAGE_MODEL` | Model id | `None` | ⚠️ |

## Providers — Video

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `VIDEO_PROVIDER` | `mock` \| `runway` \| `luma` \| `replicate` \| `stability` | `mock` | ⚠️ |
| `VIDEO_API_KEY` | Provider key | `None` | ⚠️ |
| `VIDEO_MODEL` | Model id | `None` | ⚠️ |

## Providers — TTS

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `TTS_PROVIDER` | `mock` \| `elevenlabs` \| `openai` \| `google` | `mock` | ⚠️ |
| `TTS_API_KEY` | Provider key | `None` | ⚠️ |
| `TTS_VOICE_MALE` | Default male voice id | `en-US-male` | ➖ |
| `TTS_VOICE_FEMALE` | Default female voice id | `en-US-female` | ➖ |

## Providers — Music

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `MUSIC_PROVIDER` | `mock` \| `suno` \| `udio` \| `replicate` | `mock` | ⚠️ |
| `MUSIC_API_KEY` | Provider key | `None` | ⚠️ |
| `MUSIC_MODEL` | Model id | `None` | ⚠️ |

## Payments (Razorpay)

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `PAYMENT_PROVIDER` | Payment adapter | `razorpay` | ➖ |
| `RAZORPAY_KEY_ID` | Public key id | `None` | ⚠️ |
| `RAZORPAY_KEY_SECRET` | Server-side secret — never returned by any API | `None` | ⚠️ |
| `RAZORPAY_WEBHOOK_SECRET` | HMAC secret for webhook signature verification | `None` | ⚠️ required if webhooks are live |

With keys absent the payments adapter operates in mock mode.

## Email / notifications

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `EMAIL_PROVIDER` | `mock` \| `smtp` | `mock` | ⚠️ |
| `SMTP_HOST` | SMTP server | `None` | ⚠️ |
| `SMTP_PORT` | SMTP port | `587` | ⚠️ |
| `SMTP_USER` | SMTP username | `None` | ⚠️ |
| `SMTP_PASSWORD` | SMTP password | `None` | ⚠️ |
| `SMTP_FROM` | From address | `noreply@hackroot.studio` | ⚠️ |

## Billing / credits

Plans, credits, subscriptions and invoices are **database-driven**, not
env-driven. Relevant model defaults (`app/models/user.py`,
`app/models/billing.py`):

| Setting | Where | Default |
|---|---|---|
| Starting credits per user | `users.credits_total` | `100` |
| Credits consumed | `users.credits_used` | `0` |
| Credits granted by a plan | `subscription_plans.credits_per_month` | `0` |
| Team member role | `team_members.role` | `viewer` |

Plans are seeded at startup (`app/seed.py`) and editable via
`PATCH /api/v1/admin/plans/{id}`; credits can be granted with
`POST /api/v1/admin/users/{uid}/credits`.

## Rendering (FFmpeg)

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `FFMPEG_BIN` | ffmpeg executable | `ffmpeg` | ➖ |
| `FFPROBE_BIN` | ffprobe executable | `ffprobe` | ➖ |
| `VIDEO_CODEC` | Video codec | `libx264` | ➖ |
| `VIDEO_PRESET` | x264 preset (speed/size trade-off) | `medium` | ➖ |
| `VIDEO_CRF` | Quality; lower = better/larger | `20` | ➖ |
| `AUDIO_CODEC` | Audio codec | `aac` | ➖ |
| `AUDIO_BITRATE` | Audio bitrate | `192k` | ➖ |

## Generation defaults

| Variable | Purpose | Default |
|---|---|---|
| `DEFAULT_DURATION` | Target seconds | `20` |
| `DEFAULT_ASPECT_RATIO` | Aspect ratio | `9:16` |
| `DEFAULT_LANGUAGE` | Script language | `English` |
| `DEFAULT_STYLE` | Visual style | `Cinematic` |

## Security / limits

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `MAX_UPLOAD_SIZE_MB` | Application upload cap | `50` | ➖ (nginx caps at 25 m — the tighter limit wins) |
| `RATE_LIMIT_PER_MINUTE` | Per-IP requests/minute. Declared twice in `config.py`; the **later declaration wins, so the effective default is 60**. Enforced only when `APP_ENV=production` | `60` | ➖ |

nginx adds independent limits: `api` 20 r/s burst 40, `login` 5 r/s burst 10.

## CORS

`CORS_ORIGINS` is read by `config.py` (`cors_origins`, comma-separated) and applied
in `app/main.py` via `settings.cors_origin_list()`. Set it to the browser origins your
frontend is served from:

```bash
CORS_ORIGINS=https://app.hackroot.studio,https://api.hackroot.studio
```

In non-production, `main.py` falls back to the hardcoded dev list
(`frontend_base_url`, `http://localhost:3000`, `http://127.0.0.1:3000`). In production,
only the origins in `CORS_ORIGINS` are allowed (`allow_credentials=True`).

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `CORS_ORIGINS` | Comma-separated allowed browser origins | `http://localhost:3000,http://127.0.0.1:3000` | ✅ |
| `FRONTEND_BASE_URL` | Base URL of the web app (also appended to dev CORS list) | `http://localhost:3000` | ✅ |

## Frontend

| Variable | Purpose | Default | Prod |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Browser-visible API base; baked in at build time | `http://localhost:8000` (dev) / `https://api.hackroot.studio` (prod) | ✅ |
| `NODE_ENV` | Set to `production` by `docker-compose.prod.yml` | `production` | ➖ |

## Ignored legacy keys in `production.env.example`

These are **not** read by `config.py`. Use the replacement instead.

| Legacy key | Use instead |
|---|---|
| `SECRET_KEY` | `APP_SECRET_KEY` |
| `JWT_SECRET_KEY` | `JWT_SECRET` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `JWT_EXPIRES_MINUTES` |
| `STORAGE_BASE_PATH` | `STORAGE_LOCAL_ROOT` |
| `CORS_ORIGINS` | `FRONTEND_BASE_URL` (hardcoded list) |
| `POSTGRES_HOST` / `POSTGRES_PORT` | folded into `DATABASE_URL` |

Also note: `production.env.example` states the app refuses to start on empty
secrets. **That validation is not implemented in RC-6** — run the pre-flight
check in [DEPLOYMENT.md](DEPLOYMENT.md#3-pre-flight-config-validation).
