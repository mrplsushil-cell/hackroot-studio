# LOGGING

Where logs come from, how to read them, how to stop them filling the disk, and
what must never appear in them.

```bash
export COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
```

---

## 1. Log sources

| Source | Destination | Format |
|---|---|---|
| Backend (Uvicorn + app) | container stdout/stderr → Docker json-file | `%(asctime)s [%(levelname)s] %(name)s: %(message)s` plus Uvicorn access lines |
| Celery worker | container stdout → Docker json-file | Celery `--loglevel=info` |
| nginx access | `/var/log/nginx/access.log` **inside the container** | custom `main` format |
| nginx error | `/var/log/nginx/error.log` (level `warn`) | nginx default |
| Postgres | container stdout → Docker json-file | postgres default |
| Redis | container stdout → Docker json-file | redis default |
| Request/audit log | **PostgreSQL `request_logs` table** | structured rows |

Application logging is configured in `app/main.py`:

```python
logging.basicConfig(level=settings.log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("hackroot")
```

Control verbosity with `LOG_LEVEL` (default `INFO`; use `DEBUG` only
temporarily — it is noisy and increases the chance of sensitive values reaching
logs from third-party libraries).

## 2. Reading logs

```bash
$COMPOSE logs -f backend                 # follow API
$COMPOSE logs -f worker                  # follow renders
$COMPOSE logs --since 1h --tail 200 backend worker
$COMPOSE logs backend | grep -iE 'error|traceback|unhandled'

# nginx logs live inside the container
$COMPOSE exec nginx tail -f /var/log/nginx/access.log
$COMPOSE exec nginx tail -50 /var/log/nginx/error.log
```

Notable application log lines:

- `Hackroot Studio starting (env=production)` — lifespan startup
- `Storage init warning: …` — `/data/storage` unwritable, renders will fail
- `init_db skipped: …` / `seed skipped: …` — startup best-effort steps
- `Could not mount /media: …` — local media will 404
- `Unhandled error` + traceback — from the global exception handler

## 3. Log rotation

Docker's default `json-file` driver has **no size limit** — an unrotated backend
container can fill the disk and take Postgres down with it. Configure rotation
explicitly.

### Per-service (recommended, explicit)

Add to each service in `docker-compose.prod.yml`:

```yaml
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
```

That caps each container at 250 MB (5 × 50 MB rotated files).

### Host-wide default

`/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "5" }
}
```

```bash
sudo systemctl restart docker      # applies to newly created containers only
```

Verify:

```bash
docker inspect --format '{{json .HostConfig.LogConfig}}' \
  $($COMPOSE ps -q backend)
du -sh /var/lib/docker/containers/*/*-json.log | sort -h | tail
```

### nginx logs

nginx writes to files inside its own container layer, so Docker log rotation
does **not** cover them. Either:

- bind-mount `./logs/nginx:/var/log/nginx` and rotate on the host with
  logrotate (`daily`, `rotate 14`, `compress`, `copytruncate`), or
- send them to stdout so the Docker driver handles them:
  ```
  access_log /dev/stdout main;
  error_log  /dev/stderr warn;
  ```

The second option is the simplest and makes `docker compose logs nginx` useful.

### Database-backed request log

`request_logs` grows one row per production request and is not rotated. Prune it:

```sql
DELETE FROM request_logs WHERE created_at < now() - interval '30 days';
```

Schedule this monthly (cron + `psql`), or the table becomes the largest object
in your backups.

## 4. Request and audit logging

When `APP_ENV=production`, the `rate_limit_and_log` middleware in `app/main.py`
records, per request:

| Field | Source |
|---|---|
| `user_id` | decoded from the `Authorization: Bearer` JWT (`sub`), `NULL` if anonymous/invalid |
| `method` | HTTP verb |
| `path` | `request.url.path` |
| `status_code` | response status |
| `ip` | `request.client.host` |
| `latency_ms` | measured around `call_next` |

Notes:

- In `development`/test the middleware short-circuits — **no rate limiting and
  no audit rows outside production**.
- The write is best-effort inside a bare `try/except`: if the DB insert fails
  the request still succeeds and the audit row is lost silently.
- `request.client.host` behind nginx is the proxy's address unless you resolve
  the real client from `X-Forwarded-For`; nginx does set
  `X-Real-IP` / `X-Forwarded-For`, and Uvicorn runs with `--proxy-headers
  --forwarded-allow-ips='*'`. Use the nginx `$remote_addr` field for
  authoritative client IPs.
- Rate-limit rejections return `429 {"detail":"Rate limit exceeded"}` and are
  visible in the nginx access log.

Admin read access: `GET /api/v1/admin/logs/requests` and
`GET /api/v1/admin/audit-logs`.

## 5. Secret handling — nothing sensitive in logs

Rules enforced by the current code, and rules you must keep:

- **Never log secrets.** No credential, API key, JWT, webhook secret, or
  password may be written to any log. The Razorpay secret is documented as
  server-side-only and is never returned by an API; keep it out of logs too.
- **`APP_DEBUG=false` in production.** With debug on, the global exception
  handler returns `str(exc)` and the exception class to the client — tracebacks
  can carry connection strings and query fragments. In production it returns a
  flat `{"detail":"Internal server error"}` while the full traceback goes to the
  server log only.
- **Tracebacks are server-side.** `log.exception("Unhandled error")` writes the
  stack to container logs; treat those logs as sensitive and restrict access.
- **URLs are logged, bodies are not.** `request_logs` and the nginx access log
  store method + path only. Never move secrets into query strings — put them in
  headers or the body.
- **Authorization headers are never persisted.** The middleware decodes the
  bearer token to extract `sub` and discards it.
- **Redact before sharing.** Scrub emails, IPs and IDs before pasting logs into
  tickets or chats.
- **Sentry.** If `SENTRY_DSN` is set, enable `send_default_pii=False` and
  configure `before_send` scrubbing; error payloads include local variables by
  default.
- **`production.env` never enters a log or a commit.** `chmod 600`, keep it out
  of git, and don't `echo` it in CI.

Quick audit that no obvious secret leaked:

```bash
$COMPOSE logs --since 24h \
  | grep -iE 'sk-[A-Za-z0-9]|password=|secret=|Bearer [A-Za-z0-9_-]{20,}|rzp_(live|test)_' \
  | head
```

An empty result is the expected outcome. Any hit means rotate the exposed
credential immediately, then fix the log statement.

## 6. Centralised logging (optional)

Because every service (except nginx by default) logs to stdout, shipping is
straightforward:

- **Loki + Promtail** — scrape the Docker socket, label by `compose_service`;
  pairs with the Grafana setup in [MONITORING.md](MONITORING.md).
- **Vector / Fluent Bit** — flexible routing with redaction filters applied
  before the data leaves the host.
- **Docker logging drivers** — swap `json-file` for `journald`, `gelf`, or
  `awslogs` per service if you already run that infrastructure.

Whichever you pick, apply the redaction rules from §5 at the shipper, not only
at the source.
