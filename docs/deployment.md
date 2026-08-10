# Deployment Guide — Hackroot Studio

Production-ready deployment for the Hackroot Studio SaaS platform.

## 1. Architecture

```
                 ┌──────────────┐
   Internet ───▶ │   nginx:80   │  (TLS-ready, security headers, gzip, rate-limit)
                 │   nginx:443  │
                 └──────┬───────┘
            ┌───────────┼───────────────┐
            ▼                           ▼
     ┌─────────────┐            ┌──────────────┐
     │  frontend   │            │   backend    │  FastAPI + Celery
     │  (Next.js)  │            │  :8000       │
     └─────────────┘            └──┬───────┬───┘
                                   │       │
                              ┌────▼──┐ ┌───▼────┐
                              │redis  │ │postgres│
                              │ :6379 │ │ :5432  │
                              └───────┘ └────────┘
                                   ▲
                              ┌────┴──────┐
                              │  worker   │  Celery (FFmpeg renders)
                              └───────────┘
```

The `nginx` service is the only published port (80/443). Postgres and Redis are
**not** exposed to the host in production.

## 2. Prerequisites

- Docker Engine 24+ and Docker Compose v2
- A Linux host with ~4 vCPU / 8 GB RAM minimum (FFmpeg rendering is CPU-heavy)
- (Optional) a domain + TLS certificate for `app.hackroot.studio` and `api.hackroot.studio`
- (Optional) Razorpay + SMTP credentials for live billing/email

## 3. Deploy

```bash
# 1. Configure environment
cp production.env.example production.env
nano production.env            # set strong secrets, domain, providers

# 2. (Optional) place TLS certs
mkdir -p certs
cp fullchain.pem certs/ && cp privkey.pem certs/
# then uncomment the cert lines in nginx/nginx.conf + the 80->443 redirect

# 3. Bring up
docker compose -f docker-compose.prod.yml --env-file production.env up -d --build

# 4. Verify
curl -f http://localhost/health            # nginx -> backend /health
docker compose -f docker-compose.prod.yml ps   # all healthy
```

First boot runs `alembic upgrade head` automatically inside the backend
container, then starts uvicorn. The worker joins the same Celery broker.

## 4. Environment validation

`app/config.py` validates required variables when `APP_ENV=production`:
`SECRET_KEY`, `JWT_SECRET_KEY`, and `DATABASE_URL` must be non-empty, and
`SECRET_KEY` must differ from the development default. The backend refuses to
start otherwise (fail-fast).

## 5. Log rotation

Use Docker's built-in json-file log driver with rotation (add to
`/etc/docker/daemon.json` or per-service `logging:`):

```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "5" }
}
```

nginx logs are written to `/var/log/nginx/` inside the container; mount a volume
if you need host-side retention. Application logs stream to stdout/stderr and
are captured by the driver above. Postgres/Redis also respect the same driver.

## 6. Backup strategy

### PostgreSQL (primary)
Schedule a nightly logical dump:

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > backup/db_$(date +%F).sql.gz
```
Retain 30 daily + 12 monthly. Store off-host (S3 / object storage).

### Object storage (videos, thumbnails, logos)
If `STORAGE_BACKEND=local`, the `storage_data` volume holds all media. Back it
up with a periodic `tar`/`restic` snapshot:

```bash
docker run --rm -v hackrootai_storage_data:/data -v $PWD:/backup busybox \
  tar czf /backup/storage_$(date +%F).tgz -C /data .
```
If `STORAGE_BACKEND=s3`, rely on S3 bucket versioning + lifecycle rules.

### Restore
```bash
# DB
gunzip -c backup/db_2026-08-03.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" "$POSTGRES_DB"

# Storage (local)
docker run --rm -v hackrootai_storage_data:/data -v $PWD:/backup busybox \
  tar xzf /backup/storage_2026-08-03.tgz -C /data
```
See `docs/BACKUP_RESTORE.md` (generated alongside this guide) for the full runbook.

## 7. Going live with payments / email

- **Razorpay**: fill `RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET`. Webhooks hit
  `POST /api/v1/billing/webhook`. The secret is verified server-side and never
  exposed via any endpoint. With keys absent, checkout/verify run in **mock**
  mode (no real charge) so the full flow is testable offline.
- **Email**: set `EMAIL_PROVIDER=smtp` + `SMTP_*`. With keys absent, email runs
  in **mock** mode (logged, not sent) and the config status is surfaced in the
  admin/settings UI instead of failing.

## 8. Scaling

- Increase Celery concurrency: `celery ... worker --concurrency=N` (one container
  per host, or scale the `worker` service: `docker compose up -d --scale worker=3`).
- Multiple backend replicas behind nginx are stateless (sessions are JWT, results
  in Redis/Postgres).
- For high video volume, mount a faster volume for `/data/storage` and consider
  S3 storage + a CDN in front of it.
