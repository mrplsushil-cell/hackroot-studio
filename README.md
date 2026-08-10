# Hackroot Studio

**Create. Imagine. Generate.** — an AI-powered vertical-video generation SaaS.

Hackroot Studio turns a prompt (or a product image + brief) into a rendered
short-form vertical video: script → scenes → images/clips → voice-over → music →
FFmpeg composite. It ships with a full SaaS layer (plans, credits, invoices,
teams, API keys, admin console).

Release: **RC-6**

---

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.111, Python 3.11, Uvicorn |
| ORM / DB | SQLAlchemy 2.0 (asyncio) + asyncpg, PostgreSQL 16, Alembic migrations |
| Async jobs | Celery 5.4 + Redis 7 (broker db 1, results db 2) |
| Rendering | FFmpeg / FFprobe (`libx264` + `aac`) inside the backend image |
| Frontend | Next.js 14.2 (App Router), Node 20 |
| Reverse proxy | nginx 1.27-alpine (TLS-ready, gzip, rate limits, security headers) |
| Auth | JWT (python-jose, HS256) + bcrypt password hashing |
| Payments | Razorpay (optional; mock mode when keys absent) |
| Storage | Local volume `/data/storage` (default) or S3-compatible |

All AI providers default to `mock`, so the whole product runs end-to-end with
**zero API keys**.

## Repository layout

```
backend/                FastAPI service
  app/main.py           app entrypoint, CORS, rate-limit + audit middleware
  app/config.py         all environment settings (pydantic-settings)
  app/api/v1/           auth, videos, assets, templates, brand-kit, providers,
                        agents, settings, billing, team, admin, public-api
  app/jobs/             celery_app.py + tasks.py
  app/pipeline/         generation pipeline stages
  app/providers/        llm / image / video / tts / music / payments adapters
  app/rendering/        FFmpeg composition
  alembic/versions/     0001_initial, 0002_asset_ordering, 0003_saas_billing
frontend/               Next.js 14 App Router UI
nginx/nginx.conf        production reverse proxy
docker-compose.yml      local development stack
docker-compose.prod.yml production stack (nginx + immutable images)
production.env.example  production env template
docs/                   deployment.md, BACKUP_RESTORE.md
```

## Quick start (local, Docker)

```bash
cp .env.example .env
docker compose up --build
```

Then:

- Frontend — <http://localhost:3000>
- API — <http://localhost:8000>
- Interactive API docs — <http://localhost:8000/docs>
- Health — <http://localhost:8000/health>

The backend container runs `alembic upgrade head` before starting Uvicorn, and
seeds system templates/plans on startup.

Create your first account via the UI or:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"ChangeMe123!","full_name":"You"}'
```

New users start with 100 credits. There is **no auto-created admin** — see
[INSTALL.md](INSTALL.md#promoting-an-admin) to promote a user to superuser.

## API surface

All versioned routes are under `/api/v1`:

`/auth` · `/videos` · `/assets` · `/templates` · `/brand-kit` · `/providers` ·
`/agents` · `/settings` · `/billing` · `/team` · `/admin` — plus a separately
mounted public API router. Unversioned meta routes: `/`, `/health`, `/docs`,
`/media/*` (local storage only).

See [API_REFERENCE.md](API_REFERENCE.md) for endpoint detail.

## Documentation

| Doc | Contents |
|---|---|
| [INSTALL.md](INSTALL.md) | Local dev setup (Docker and bare-metal) |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deploy: compose.prod + nginx + TLS |
| [ENVIRONMENT.md](ENVIRONMENT.md) | Every environment variable, grouped |
| [BACKUP.md](BACKUP.md) | pg_dump + storage volume backup, retention |
| [RECOVERY.md](RECOVERY.md) | Restore procedures and verification |
| [MONITORING.md](MONITORING.md) | Health, queue depth, 5xx, credits, disk |
| [LOGGING.md](LOGGING.md) | Log sources, rotation, audit logs, secrets |
| [API_REFERENCE.md](API_REFERENCE.md) | HTTP API reference |
| [SECURITY_REPORT.md](SECURITY_REPORT.md) | Security posture review |
| [LAUNCH_CHECKLIST.md](LAUNCH_CHECKLIST.md) | Go-live checklist |
| [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md) | Original combined runbook |

## License

Proprietary — © Hackroot Studio. All rights reserved.
