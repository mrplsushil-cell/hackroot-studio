# MONITORING

What to watch on a production Hackroot Studio deployment, how to check it with
nothing but Docker and `curl`, and where to escalate to real tooling.

```bash
export COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
```

---

## 1. Container health

`docker-compose.prod.yml` defines health checks for four services:

| Service | Check | Interval / timeout / retries |
|---|---|---|
| `postgres` | `pg_isready -U $POSTGRES_USER` | 10s / 5s / 5 |
| `redis` | `redis-cli ping` | 10s / 5s / 5 |
| `backend` | `curl -f http://localhost:8000/health` | 30s / 10s / 3 |
| `frontend` | `wget -qO- http://localhost:3000/` | 30s / 10s / 3 |
| `nginx` | `wget -qO- http://localhost/health` | 30s / 10s / 3 |

`worker` has **no health check** — Celery workers are monitored via ping and
queue depth (§2).

```bash
$COMPOSE ps                                    # STATUS column shows (healthy)
docker inspect --format '{{.Name}} {{.State.Health.Status}}' $($COMPOSE ps -q)
$COMPOSE ps --filter status=exited             # restart-loop detection
```

External probe (what your uptime monitor should hit):

```bash
curl -fsS https://api.hackroot.studio/health
# {"ok":true,"app":"Hackroot Studio","env":"production"}
```

**Alert:** any service not `healthy` for 2 consecutive minutes; `/health`
non-200 or >2 s; restart count increasing.

## 2. Celery queue depth and worker liveness

Broker is Redis **db 1**; results are in **db 2**. The default queue name is
`default` (`task_default_queue="default"` in `app/jobs/celery_app.py`) — it is
*not* `celery`.

```bash
# pending tasks waiting for a worker
$COMPOSE exec redis redis-cli -n 1 llen default

# discover queue keys if you add routing later
$COMPOSE exec redis redis-cli -n 1 keys '*'

# live workers + what they're running
$COMPOSE exec worker celery -A app.jobs.celery_app inspect ping
$COMPOSE exec worker celery -A app.jobs.celery_app inspect active
$COMPOSE exec worker celery -A app.jobs.celery_app inspect stats
```

Thresholds (tune to your traffic):

| Signal | Warn | Critical |
|---|---|---|
| `llen default` | > 20 for 5 min | > 100, or rising for 15 min |
| `inspect ping` replies | fewer than expected replicas | zero replies |
| Video job stuck in `processing` | > 15 min | > 30 min |

A rising queue with healthy workers means you are CPU-bound on FFmpeg — scale
with `up -d --scale worker=N` ([DEPLOYMENT.md](DEPLOYMENT.md#6-scaling-the-worker)).
Zero ping replies with a growing queue means the worker container is dead or
pointed at the wrong broker.

`task_acks_late=True` means a killed worker's task returns to the queue — a
persistent slow rise can also indicate a task that repeatedly crashes the
worker. Cross-check `$COMPOSE logs worker | grep -i traceback`.

## 3. HTTP error rate (5xx) and latency

Two sources, both already produced by the stack.

### nginx access log

`log_format main` includes `$status` and `rt=$request_time`:

```bash
# 5xx in the last 1000 requests
$COMPOSE exec nginx sh -c \
  "tail -1000 /var/log/nginx/access.log | awk '{print \$9}' | sort | uniq -c | sort -rn"

# slowest recent requests
$COMPOSE exec nginx sh -c \
  "tail -2000 /var/log/nginx/access.log | grep -o 'rt=[0-9.]*' | sort -t= -k2 -rn | head"

# 429s = rate limiting is biting (api zone 20r/s, login zone 5r/s)
$COMPOSE exec nginx sh -c "grep -c ' 429 ' /var/log/nginx/access.log"
```

### In-app request log

When `APP_ENV=production`, the middleware in `app/main.py` writes every request
to the `request_logs` table (`user_id`, `method`, `path`, `status_code`, `ip`,
`latency_ms`).

```sql
-- 5xx rate, last hour
SELECT count(*) FILTER (WHERE status_code >= 500)::float
       / NULLIF(count(*),0) AS error_rate, count(*) AS total
FROM request_logs WHERE created_at > now() - interval '1 hour';

-- slowest endpoints
SELECT path, count(*), avg(latency_ms)::int AS avg_ms, max(latency_ms) AS max_ms
FROM request_logs WHERE created_at > now() - interval '1 hour'
GROUP BY path ORDER BY avg_ms DESC LIMIT 15;
```

Also exposed to admins at `GET /api/v1/admin/logs/requests` and
`GET /api/v1/admin/audit-logs`.

**Alert:** 5xx rate > 1% over 5 min; p95 latency > 2 s on non-`/videos` routes;
any sustained 429 spike (either an attack or a limit set too low).

> `request_logs` grows with every request. Prune it on a schedule, e.g.
> `DELETE FROM request_logs WHERE created_at < now() - interval '30 days';`

## 4. Credit consumption and business signals

Credits live on `users` (`credits_total`, `credits_used`); plans carry
`credits_per_month`.

```sql
-- credits burned in the last 24h (requires historical snapshots; use as a gauge)
SELECT sum(credits_used) AS used, sum(credits_total) AS granted FROM users;

-- accounts near exhaustion
SELECT id, email, credits_total - credits_used AS remaining
FROM users WHERE credits_total - credits_used < 10 ORDER BY remaining;

-- generation throughput / failure rate
SELECT status, count(*) FROM videos
WHERE created_at > now() - interval '24 hours' GROUP BY status;
```

`GET /api/v1/admin/stats` and `GET /api/v1/admin/analytics` surface the same
aggregates through the API.

**Alert:** video `failed` share > 5% of the last 24 h; a sudden jump in
`credits_used` (runaway loop or abuse); paid-provider spend rising while
`*_PROVIDER` is not `mock`.

## 5. Disk — `/data/storage`

Rendered MP4s accumulate on the `storage_data` volume and nothing prunes them
automatically.

```bash
$COMPOSE exec backend df -h /data/storage
$COMPOSE exec backend du -sh /data/storage
docker system df -v | grep storage_data

# host-level docker root
df -h /var/lib/docker
```

**Alert:** < 20% free = warn, < 10% free = critical. A full disk breaks FFmpeg
renders *and* Postgres writes simultaneously.

Mitigations: move to `STORAGE_BACKEND=s3`; add a retention job deleting media
for videos older than N days; raise `VIDEO_CRF` or use a faster
`VIDEO_PRESET` to shrink outputs. Also watch Postgres growth
(`SELECT pg_size_pretty(pg_database_size(current_database()));`) — `request_logs`
is usually the biggest table.

## 6. Redis memory

Configured with `--maxmemory 512mb --maxmemory-policy allkeys-lru`. Under LRU,
eviction can silently drop task results.

```bash
$COMPOSE exec redis redis-cli info memory | grep -E 'used_memory_human|maxmemory_human'
$COMPOSE exec redis redis-cli info stats | grep evicted_keys
```

**Alert:** `evicted_keys` > 0, or `used_memory` > 80% of maxmemory.

## 7. Host resources

```bash
docker stats --no-stream
uptime; free -h; nproc
```

FFmpeg saturates CPU by design. Sustained load average above core count with a
growing queue is the scale-out signal.

## 8. Optional tooling

RC-6 exposes **no `/metrics` endpoint** — there is no Prometheus instrumentation
in the code. Options, cheapest first:

1. **Uptime checks** (UptimeRobot, Healthchecks.io, Better Stack) against
   `/health` — 5 minutes of setup, covers most real outages.
2. **Sentry** — `sentry-sdk==2.5.0` is already in `requirements.txt`; set
   `SENTRY_DSN` to capture unhandled exceptions from the API and worker.
3. **cAdvisor + node_exporter + Prometheus + Grafana** — container CPU/mem/disk
   and host metrics with no application changes.
4. **redis_exporter** — scrape `llen default`, memory, evictions as real
   Prometheus series.
5. **postgres_exporter** — connections, DB size, slow queries.
6. **Loki/Promtail** or an ELK stack — ship the JSON container logs described in
   [LOGGING.md](LOGGING.md).
7. **App-level Prometheus** — adding `prometheus-fastapi-instrumentator` and a
   Celery exporter is the natural next step; it is a code change, not config.

## 9. Suggested daily check

```bash
$COMPOSE ps
curl -fsS https://api.hackroot.studio/health
$COMPOSE exec redis redis-cli -n 1 llen default
$COMPOSE exec backend df -h /data/storage
$COMPOSE logs --since 24h backend worker | grep -iE 'error|traceback' | tail -20
ls -lh backup/ | tail -3        # last night's backup landed
```
