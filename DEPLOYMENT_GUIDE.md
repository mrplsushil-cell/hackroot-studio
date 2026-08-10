# Deployment Guide

Quick reference for deploying Hackroot Studio to production. Full runbook in
`docs/deployment.md` and `docs/BACKUP_RESTORE.md`.

## Prerequisites
- Docker Engine 24+ and Docker Compose v2
- Domain(s) for `app.hackroot.studio` and `api.hackroot.studio` (optional)
- TLS certificate (optional but recommended)
- Razorpay + SMTP credentials (optional — mock mode otherwise)

## Steps

```bash
# 1. Configure environment (NEVER commit the result)
cp production.env.example production.env
nano production.env        # set SECRET_KEY, JWT_SECRET_KEY, POSTGRES_PASSWORD, domains

# 2. (Optional) TLS — place certs and uncomment cert lines in nginx/nginx.conf
mkdir -p certs && cp fullchain.pem privkey.pem certs/

# 3. Build & start (nginx is the only published port)
docker compose -f docker-compose.prod.yml --env-file production.env up -d --build

# 4. Verify
curl -f http://localhost/health
docker compose -f docker-compose.prod.yml ps
```

## Architecture
```
Internet → nginx (:80/:443) → frontend (:3000) | backend (:8000)
backend → postgres (:5432, internal) | redis (:6379, internal, Celery broker)
worker (Celery) → FFmpeg renders → storage volume
```

## Environment Validation
`app/config.py` fails fast in production if `SECRET_KEY`, `JWT_SECRET_KEY`, or
`DATABASE_URL` are empty, or if `SECRET_KEY` equals the dev default.

## Log Rotation
Docker json-file driver: `max-size=50m`, `max-file=5` (see deployment.md).

## Backup / Restore
- DB: nightly `pg_dump` → gzip → off-host retention 30 daily + 12 monthly.
- Storage: periodic `tar` of the `storage_data` volume (or S3 versioning).
- See `docs/BACKUP_RESTORE.md` for the full runbook + restore procedures.

## Scaling
- Worker: `docker compose -f docker-compose.prod.yml up -d --scale worker=3`
- Backend: stateless (JWT + Redis/Postgres), add replicas behind nginx.
- High volume: S3 storage + CDN; faster volume for `/data/storage`.

## Going Live
- **Payments**: set `RAZORPAY_KEY_ID/SECRET/WEBHOOK_SECRET`. Webhooks:
  `POST /api/v1/billing/webhook`.
- **Email**: set `EMAIL_PROVIDER=smtp` + `SMTP_*`. Config status is visible in
  `/settings` (admin) — no silent failures.
