# DEPLOYMENT_COMPLETE — Hackroot Studio v1.0 (Production)

**Date:** 2026-08-03
**Status:** ✅ Production deployment configuration complete and verified end-to-end.

This document records the production deployment work and the verification evidence
collected by deploying the stack with `docker-compose.prod.yml` on a local host
(HTTPS served via a self-signed certificate to exercise the full TLS path).

---

## What was delivered

### 1. Production Docker
- **Multi-stage backend Dockerfile** (`backend/Dockerfile`): builder stage compiles
  wheels into a venv; slim runtime stage carries only `ffmpeg`, `libpq`, `espeak-ng`,
  CJK/emoji fonts, runs as a non-root `app` user, uses `tini` for PID 1. Build
  tooling is excluded from the runtime image.
- **Frontend** already multi-stage (deps → builder → runner).
- **`docker-compose.prod.yml`**: nginx + frontend + backend + worker + postgres +
  redis + certbot, with `restart: unless-stopped`, per-service **healthchecks**,
  internal-only postgres/redis (no host-exposed ports), and **Docker json-file log
  rotation** (`max-size=50m`, `max-file=5`) applied to every service via a YAML anchor.

### 2. Nginx (`nginx/nginx.conf` + `nginx/Dockerfile`)
- Reverse proxy: `/api/*` → backend, `/media/*` → backend storage, `/_next/static/`
  → frontend, rest → frontend SPA.
- **HTTP → HTTPS 301 redirect** (ACME challenge path exempt).
- **Gzip** + **Brotli** (built locally from Alpine's `nginx` + `nginx-mod-http-brotli`,
  ABI-matched — verified serving `Content-Encoding: br`).
- **HSTS** (`max-age=63072000; includeSubDomains; preload`).
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`,
  `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`.
- **Cache headers**: `/_next/static/` immutable 1y; `/media/` 1d.
- **Upload limit** `client_max_body_size 50m` (covers brand-kit logos + product images).
- Per-zone rate limiting (`api` 20r/s, `login` 5r/s) as defence in depth.

### 3. SSL — Let's Encrypt (automatic)
- `certbot` service issues certs via webroot and auto-renews every 12h.
- nginx serves TLS from the `certs` volume; documented renewal hook reloads nginx.
- `SSL_SETUP.md` covers staging/testing, multi-domain issuance, and verification.

### 4. Monitoring & Logging
- App health endpoint `/health` (proxied at `https://<host>/health`).
- Docker healthchecks on every public service.
- json-file log rotation on all containers.
- `MONITORING.md` / `LOGGING.md` document Celery queue depth (`redis-cli -n 1 llen default`),
  5xx rate, credit consumption, and disk growth on `/data/storage`.

### 5. Backup & Restore
- `scripts/backup.sh`: nightly `pg_dump` (covers Brand Kits + Templates tables) +
  `storage_data` tarball (covers brand-kit logos, product images, generated media).
  Retention via `RETENTION_DAYS` (default 30).
- `scripts/restore.sh`: stops writers, restores DB + storage from a single stamp,
  restarts. `BACKUP.md` / `RECOVERY.md` document the procedure.
- `scripts/deploy.sh`: up / upgrade / rollback / backup / logs helpers.

### 6. Deployment Guide
- `DEPLOYMENT.md` (step-by-step Ubuntu 24.04 deploy / upgrade / rollback).
- `VPS_SETUP.md`, `DOMAIN_SETUP.md`, `SSL_SETUP.md`, `SERVER_REQUIREMENTS.md`.

---

## Final Verification Evidence

The stack was deployed with `docker compose -p hackrootprod -f docker-compose.prod.yml
--env-file production.env up -d --build` and exercised through the nginx TLS endpoint.

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | HTTPS (TLS termination) | ✅ | `GET https://localhost/health` → `200` |
| 2 | HTTP→HTTPS redirect | ✅ | `GET http://localhost/health` → `301` |
| 3 | HSTS + security headers | ✅ | `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options` present |
| 4 | Brotli | ✅ | `Content-Encoding: br` on response |
| 5 | Gzip | ✅ | `Content-Encoding: gzip` on API JSON |
| 6 | Registration | ✅ | `POST /auth/register` → `201` |
| 7 | Login | ✅ | `POST /auth/login` → `200` + `access_token` |
| 8 | Brand Kit create + default | ✅ | `POST /brand-kit` → `201`; `POST /brand-kit/{id}/default` → `200` |
| 9 | Templates list | ✅ | `GET /templates` → `200`, 8 templates |
| 10 | Billing plans | ✅ | `GET /billing/plans` → `200`, 4 plans |
| 11 | Video generation | ✅ | `POST /videos` → `201`; `POST /videos/{id}/generate` → `202`; status → `completed` |
| 12 | MP4 download | ✅ | `GET /videos/{id}/download` → `200 video/mp4`, ~396 KB |
| 13 | Credits deducted | ✅ | balance 100 → 99 (10s = 1 credit) |
| 14 | Public API | ✅ | `POST /api-keys` → `201`; `POST /generate-video` (Bearer key) → `202` |

### Sample responses (redacted)
```
$ curl -sk -D - -o /dev/null https://localhost/
HTTP/2 200
content-type: text/html; charset=utf-8
content-encoding: br
strict-transport-security: max-age=63072000; includeSubDomains; preload
x-content-type-options: nosniff
x-frame-options: SAMEORIGIN
content-security-policy: default-src 'self'; ...

$ curl -sk https://localhost/api/v1/auth/me   # -> credits_total 100, credits_used 1
$ curl -sk https://localhost/api/v1/videos/5/download   # -> 200 video/mp4 396063 bytes
```

---

## Notes / caveats
- Verification used a **self-signed** certificate to exercise the TLS path locally.
  In production, follow `SSL_SETUP.md` to issue a trusted Let's Encrypt cert
  (the `certbot` service + webroot challenge are already wired).
- `production.env` and `certs/` are git-ignored (secrets). They were removed after
  verification. Operators must create their own `production.env` from
  `production.env.example` with real secrets before deploying.
- Mock providers are the default; set real `LLM_*`/`IMAGE_*`/`VIDEO_*`/`TTS_*`/
  `RAZORPAY_*`/`SMTP_*` keys in `production.env` for live output.
- Pre-launch checklist (LAUNCH_CHECKLIST.md) and the security notes
  (SECURITY_REPORT.md, F-04–F-06) remain the gating items for go-live:
  real secrets, HTTPS domain, backups scheduled, monitoring wired.

**Verdict: Production deployment configuration is complete and verified. GO,
subject to the pre-launch checklist (real domain + Let's Encrypt cert, real
provider/keys, scheduled backups, monitoring).**
