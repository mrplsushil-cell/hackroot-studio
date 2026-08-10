# Launch Checklist — Hackroot Studio (v1.0.0)

Go/no-go gate before public launch. Items marked ✅ were completed and verified
during the release-candidate hardening. Unchecked items are required before launch
or are configuration steps for your environment.

## Pre-launch (must pass) ✅
- [x] All 48 backend tests pass (`pytest`)
- [x] Frontend type-checks (`tsc --noEmit`) and builds (`npm run build`)
- [x] Docker stack healthy (backend, worker, postgres, redis)
- [x] E2E generation renders a real MP4 (ffprobe: h264 720x1280, aac)
- [x] Credit deduction verified (20s → 2 credits; ledger written)
- [x] Watermark verified (free = on, paid = off)
- [x] Subsystem validation: billing, credits, library, brand-kit, templates, agents, public API
- [x] Security audit complete (SECURITY_REPORT.md)

## Docker
- [x] `docker-compose.prod.yml` validates (`docker compose -f docker-compose.prod.yml config`)
- [ ] Build images: `docker compose -f docker-compose.prod.yml --env-file production.env up -d --build`
- [ ] Confirm all 6 services start: nginx, frontend, backend, worker, postgres, redis
- [ ] Remove dev `docker-compose.yml` from production host (or isolate network)

## HTTPS / SSL
- [ ] Obtain TLS cert (Let's Encrypt or CA) → `certs/fullchain.pem`, `certs/privkey.pem`
- [ ] Mount certs in `nginx/` and uncomment the `listen 443 ssl` + cert lines
- [ ] Enable 80→443 redirect + `add_header Strict-Transport-Security`
- [ ] Verify `curl -I https://your-domain` returns 200/301

## Domain
- [ ] A/AAAA records point to the server (app + api, or single domain with paths)
- [ ] `frontend_base_url` and `app_base_url` set to real domains in `production.env`
- [ ] CORS origins set to real domains (`CORS_ORIGINS=https://app.hackroot.studio`)

## Email
- [ ] `EMAIL_PROVIDER=smtp` + `SMTP_HOST/PORT/USER/PASSWORD/FROM`
- [ ] Send a test welcome + invoice email
- [ ] Confirm `/settings` shows `email.configured: true`

## Payment (Razorpay)
- [ ] `RAZORPAY_KEY_ID` **and** `RAZORPAY_KEY_SECRET` set together (both required for signature verification)
- [ ] `RAZORPAY_WEBHOOK_SECRET` set; webhook registered → `/api/v1/billing/webhook`
- [ ] Test a real ₹1 charge in Razorpay test mode end-to-end
- [ ] Verify invoice + credit grant + `subscription_activated` notification on real payment

## Redis
- [ ] Redis reachable on internal network only (no public port)
- [ ] `redis-cli ping` → PONG
- [ ] Confirm Celery broker (`CELERY_BROKER_URL`, db 1) and result backend (db 2) resolve
- [ ] Set a Redis password / ACL for production (or private network)

## Database (PostgreSQL)
- [ ] `alembic upgrade head` applied on the production DB
- [ ] `POSTGRES_PASSWORD` is strong and stored in secrets manager
- [ ] DB not exposed publicly (bind to internal network)
- [ ] Connection pool sizing sane for expected load

## Worker (Celery)
- [ ] Worker container running: `docker compose exec worker celery -A app.jobs.celery_app status`
- [ ] Scale horizontally if needed: `docker compose -f docker-compose.prod.yml up -d --scale worker=3`
- [ ] Verify a test job drains (`redis-cli -n 1 llen default` returns 0 when idle — the Celery queue is named `default`, not `celery`)

## Backups
- [ ] Nightly `pg_dump` scheduled (see BACKUP.md / `scripts/backup.sh`)
- [ ] Storage volume backed up (or S3 versioning enabled)
- [ ] Off-host retention (30 daily + 12 monthly)
- [ ] Restore drill performed at least once (RECOVERY.md)

## Monitoring
- [ ] Container health checks (Docker `--healthcheck`) green
- [ ] Alert on 5xx rate + Celery queue depth + disk for `/data/storage`
- [ ] (Optional) Prometheus/Grafana scrape of app metrics

## Cron Jobs
- [ ] Backup cron installed (e.g. `0 3 * * * docker compose exec postgres pg_dump ...`)
- [ ] Log rotation cron / Docker json-file `max-size=50m max-file=5` confirmed
- [ ] (Optional) credit expiry / invoice reconciliation jobs scheduled

## API Keys
- [ ] Business customers can create keys (`POST /api-keys`); full key shown once
- [ ] Default scopes + quota reviewed per customer tier
- [ ] Revoke/rotate keys procedure documented (ADMIN_GUIDE.md)

## Environment Variables
- [ ] `production.env` created from `production.env.example`
- [ ] `APP_ENV=production`, `APP_DEBUG=false`
- [ ] `SECRET_KEY`, `JWT_SECRET` strong + unique
- [ ] No `change-me` defaults remain (config fails fast if present)

## Security
- [ ] SECURITY_REPORT.md reviewed; F-01 (Razorpay both keys) addressed
- [ ] nginx security headers present (CSP, X-Frame-Options, etc.)
- [ ] Rate limiting active (`APP_ENV=production`)
- [ ] Secrets manager holds `.env` (not committed to VCS)
- [ ] Admin user promoted via SQL (ADMIN_GUIDE.md); first admin secured

## Logging
- [ ] Log rotation active (json-file driver)
- [ ] Centralized log shipping configured (optional)
- [ ] Confirm no secrets appear in logs (email shows status only)

## CDN
- [ ] (If scaling) put `/media` behind a CDN or S3 + CloudFront
- [ ] Cache headers for thumbnails/MP4 set in nginx

## Storage
- [ ] `STORAGE_BACKEND=local` volume sized for growth (or `s3` + bucket configured)
- [ ] `/data/storage` backed up (see Backups)

## Production Secrets
- [ ] All secrets in a manager (Docker secrets / Vault / cloud KMS)
- [ ] `.env` / `production.env` git-ignored and access-controlled
- [ ] Rotate any keys that were used in non-prod

## Post-launch (optional)
- [ ] Team member acceptance flow + per-resource RBAC
- [ ] S3 + CDN for media at scale
- [ ] Stripe alternative / invoicing PDFs
- [ ] i18n email templates
- [ ] Dependency scanning in CI (`pip-audit`, `npm audit`)
