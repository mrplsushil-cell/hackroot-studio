# INSTALL — Local Development Setup

Two supported paths: **Docker (recommended)** and **bare-metal** (backend and
frontend run on the host, Postgres/Redis in Docker).

---

## 1. Prerequisites

| Tool | Version | Why |
|---|---|---|
| Docker Engine + Compose v2 | 24+ | full stack (`docker compose`, not `docker-compose`) |
| Python | 3.11 | backend image is `python:3.11-slim`; asyncpg/pydantic pinned for it |
| Node.js | 20 | frontend image is `node:20-alpine`; Next.js 14.2 |
| FFmpeg + FFprobe | any recent | video rendering (already inside the backend image) |
| PostgreSQL client (`psql`, `pg_dump`) | 16 | optional, for backups/admin |

Verify:

```bash
docker compose version
python3 --version   # 3.11.x
node --version      # v20.x
ffmpeg -version
```

## 2. Clone and configure

```bash
git clone <your-remote> "Hackroot ai"
cd "Hackroot ai"
cp .env.example .env
```

`.env.example` is the **development** template and matches
`backend/app/config.py` variable-for-variable. Defaults work as-is: every AI
provider is `mock`, so no API keys are needed. See [ENVIRONMENT.md](ENVIRONMENT.md).

For bare-metal runs, point the DB/Redis hosts at localhost in `.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://hackroot:hackroot@localhost:5432/hackroot
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
STORAGE_LOCAL_ROOT=./.storage
```

## 3. Run everything with Docker (recommended)

```bash
docker compose up --build
```

This starts five services from `docker-compose.yml`:

| Service | Port | Notes |
|---|---|---|
| `postgres` | 5432 | postgres:16-alpine, volume `postgres_data` |
| `redis` | 6379 | redis:7-alpine, volume `redis_data` |
| `backend` | 8000 | `alembic upgrade head && uvicorn app.main:app --reload`, source bind-mounted |
| `worker` | — | `celery -A app.jobs.celery_app worker --loglevel=info --concurrency=2` |
| `frontend` | 3000 | Next.js, `NEXT_PUBLIC_API_URL=http://localhost:8000` |

Shared volume `storage_data` is mounted at `/data/storage` in both `backend`
and `worker` — the worker writes renders where the API can serve them.

Check it is alive:

```bash
curl -f http://localhost:8000/health
# {"ok":true,"app":"Hackroot Studio","env":"development"}
```

Useful:

```bash
docker compose logs -f backend worker
docker compose down          # stop
docker compose down -v       # stop AND wipe DB + storage volumes
```

## 4. Bare-metal backend (optional)

Run only the datastores in Docker:

```bash
docker compose up -d postgres redis
```

Then:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

alembic upgrade head

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

In a second shell (same venv, same `.env`):

```bash
cd backend
source .venv/bin/activate
celery -A app.jobs.celery_app worker --loglevel=info --concurrency=2
```

> In `APP_ENV=development` the app also calls `init_db()` on startup as a
> convenience, but **Alembic is the source of truth** — always run
> `alembic upgrade head`.

## 5. Bare-metal frontend (optional)

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in the frontend environment.

## 6. Database migrations

```bash
# apply
docker compose exec backend alembic upgrade head
# create a new revision after model changes
docker compose exec backend alembic revision --autogenerate -m "describe change"
# inspect
docker compose exec backend alembic current
```

Existing revisions: `0001_initial`, `0002_asset_ordering`, `0003_saas_billing`.

## 7. First user and admin

### Register

Via the UI at <http://localhost:3000>, or:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"ChangeMe123!","full_name":"Admin"}'
```

Returns a JWT. New users get `credits_total = 100`, `credits_used = 0`,
`is_superuser = false`.

### Promoting an admin

**There is no default/seeded admin account.** Register a normal user first, then
flip the flag directly in Postgres:

```bash
docker compose exec postgres \
  psql -U hackroot -d hackroot \
  -c "UPDATE users SET is_superuser = true WHERE email = 'admin@example.com';"
```

Re-login (or fetch a fresh token) and the `/api/v1/admin/*` routes — stats,
users, credits grants, subscriptions, plans, invoices, videos, request logs,
audit logs, analytics — become available.

## 8. Tests

```bash
cd backend
source .venv/bin/activate
pytest -q                 # pytest, pytest-asyncio, pytest-cov, fakeredis
```

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `alembic upgrade head` fails at boot | Postgres not healthy yet; compose already gates on `service_healthy` — check `docker compose logs postgres` |
| Renders never finish | worker not running / broker mismatch: `docker compose logs -f worker`, confirm `CELERY_BROKER_URL` |
| `/media/...` 404 | `STORAGE_LOCAL_ROOT` mismatch between backend and worker, or `STORAGE_BACKEND=s3` |
| CORS errors in browser | `main.py` allows `FRONTEND_BASE_URL` plus `localhost:3000` / `127.0.0.1:3000` only — set `FRONTEND_BASE_URL` |
| Port already in use | change host port mappings in `docker-compose.yml` |
