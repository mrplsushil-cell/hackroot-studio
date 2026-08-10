# DEPLOYMENT GUIDE — Hackroot Studio v1.0 (Production)

End-to-end production deployment. Companion docs: VPS_SETUP.md, DOMAIN_SETUP.md,
SSL_SETUP.md, SERVER_REQUIREMENTS.md, BACKUP.md, RECOVERY.md, MONITORING.md,
LOGGING.md.

## 0. Architecture
```
Internet ── 80/443 ──▶ nginx (brotli + TLS) ──▶ frontend (:3000) | backend (:8000)
                                                    backend ──▶ postgres (:5432, internal)
                                                    worker  ──▶ redis (:6379, internal, Celery)
```
Only nginx publishes 80/443. Postgres and Redis are on the internal Docker
network (not host-exposed).

## 1. Host (Ubuntu 24.04 LTS)
Follow VPS_SETUP.md: update OS, install Docker Engine 24+ + Compose v2, configure
`ufw` (allow 22/80/443 only), place project at `/opt/hackroot`, `chmod 600 production.env`.

## 2. Domain & DNS
Follow DOMAIN_SETUP.md: A/AAAA for `app` + `api` → server IP; set
`NEXT_PUBLIC_API_URL`, `FRONTEND_BASE_URL`, `CORS_ORIGINS` in `production.env`.

## 3. Environment variables
```bash
cd /opt/hackroot
cp production.env.example production.env
chmod 600 production.env
nano production.env
```
Required (real values — fail-fast blocks `change-me` in production):
- `APP_SECRET_KEY`, `JWT_SECRET` — 32-byte hex (`openssl rand -hex 32`)
- `DATABASE_URL` — `postgresql+asyncpg://hackroot:<pw>@postgres:5432/hackroot`
- `POSTGRES_PASSWORD` — strong
- `NEXT_PUBLIC_API_URL`, `FRONTEND_BASE_URL`, `CORS_ORIGINS`
- `APP_ENV=production`, `APP_DEBUG=false`
- Optional live keys: `RAZORPAY_*` (both id+secret), `SMTP_*`, `LLM_*/IMAGE_*/VIDEO_*/MUSIC_*/TTS_*` providers

## 4. Firewall
```bash
sudo ufw allow OpenSSH; sudo ufw allow 80/tcp; sudo ufw allow 443/tcp; sudo ufw enable
```

## 5. Nginx
`nginx/nginx.conf` ships production-ready (brotli, gzip, HSTS, security headers,
redirect, cache, rate-limit, 50 MB upload). It mounts from the repo
(`./nginx/nginx.conf:/etc/nginx/nginx.conf:ro`). Certs mount from the `certs`
volume. No extra host config needed.

## 6. First deployment
```bash
COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
$COMPOSE config                # validate
$COMPOSE up -d --build         # build images + start; backend auto-runs alembic upgrade head
$COMPOSE ps                    # all services "running" + healthy
```
Verify:
```bash
curl -f http://localhost/health        # {"ok":true,...}
```

## 7. SSL (Let's Encrypt, automatic)
Follow SSL_SETUP.md:
```bash
$COMPOSE run --rm certbot certonly --webroot -w /var/www/certbot \
  --email admin@yourdomain.com --agree-tos -d app.yourdomain.com -d api.yourdomain.com
$COMPOSE exec nginx nginx -s reload
curl -I https://app.yourdomain.com/health   # 200 + HSTS
```
Renewal is automatic via the `certbot` service (runs `certbot renew` every 12h).

## 8. Upgrade procedure
```bash
git pull
$COMPOSE pull                         # if using remote images
$COMPOSE up -d --build --force-recreate
# migrations run automatically on backend start (alembic upgrade head)
$COMPOSE ps
```
For zero-downtime-ish: nginx stays up; backend/worker restart sequentially. To
roll back a bad image, tag the previous good image and recreate.

## 9. Rollback procedure
```bash
# If a new image is broken:
docker tag hackrootai_backend:previous hackrootai_backend:bad
$COMPOSE up -d --force-recreate backend worker
# Database: if a migration is the problem, restore the pre-upgrade backup:
./scripts/restore.sh <PRE_UPGRADE_STAMP>     # see BACKUP.md / RECOVERY.md
```
Always snapshot (`scripts/backup.sh`) immediately before an upgrade.

## 10. Backups (automated)
```bash
./scripts/backup.sh                  # db + storage tarball -> ./backup
# schedule nightly, e.g. crontab:
# 0 3 * * *  cd /opt/hackroot && ./scripts/backup.sh >> backup/cron.log 2>&1
```
Restores: RECOVERY.md (`scripts/restore.sh <STAMP>`).

## 11. Monitoring & logging
- Docker healthchecks on every service (`docker inspect --format '{{.State.Health.Status}}' <container>`).
- App endpoint `/health` (proxied at `https://app/health`).
- Logs: Docker json-file driver (`max-size=50m`, `max-file=5`). `docker compose logs -f`.
- See MONITORING.md / LOGGING.md for Celery queue depth (`redis-cli -n 1 llen default`),
  5xx rate, credit consumption, and disk growth on `/data/storage`.

## 12. Post-deploy checklist
- [ ] `/health` returns 200 (HTTP + HTTPS)
- [ ] HTTPS redirect 80→443 works
- [ ] HSTS header present
- [ ] Register a test user → generate a 10s video → download MP4
- [ ] Billing: checkout (Razorpay mock or live) → plan active, credits granted
- [ ] Brand Kit create + set default
- [ ] Templates list
- [ ] Public API: create key → `generate-video` (202)
- [ ] Backups scheduled; one restore drill done
