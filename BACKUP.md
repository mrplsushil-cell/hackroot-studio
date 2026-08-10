# BACKUP

Two stateful components must be backed up together:

| What | Where it lives | Docker volume (prod) |
|---|---|---|
| PostgreSQL 16 database | `postgres:/var/lib/postgresql/data` | `postgres_data` |
| Generated media (`/data/storage`) | `backend` + `worker` | `storage_data` |
| Redis (broker/results) | `redis:/data` | `redis_data` — **transient, not backed up** |

Redis holds only in-flight tasks and results; losing it costs at most the
currently queued renders. Do not include it in the backup rotation.

Compose prefixes volume names with the project name. From the repo directory
`Hackroot ai` the project is `hackrootai`, so the real names are
`hackrootai_postgres_data`, `hackrootai_storage_data`, `hackrootai_redis_data`.
Confirm before scripting:

```bash
docker volume ls --filter name=storage_data
docker compose -f docker-compose.prod.yml config --volumes
```

All commands assume the repo root and:

```bash
export COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
set -a; . ./production.env; set +a     # POSTGRES_USER / POSTGRES_DB
mkdir -p backup
```

---

## 1. Database — logical dump (nightly)

`pg_dump` runs inside the `postgres` container; nothing is exposed on the host
in production.

```bash
$COMPOSE exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "backup/db_$(date +%F_%H%M).sql.gz"
```

Custom format (parallel restore, selective table restore):

```bash
$COMPOSE exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" \
  > "backup/db_$(date +%F_%H%M).dump"
```

Verify the dump is non-trivial and complete before trusting it:

```bash
ls -lh backup/db_*.sql.gz | tail -1
gunzip -c backup/db_$(date +%F)*.sql.gz | tail -5   # should end with "PostgreSQL database dump complete"
```

`pg_dump` is transactionally consistent — you do **not** need to stop the app
for the DB alone.

## 2. Media storage volume

```bash
docker run --rm \
  -v hackrootai_storage_data:/data:ro \
  -v "$(pwd)/backup":/backup busybox \
  tar czf "/backup/storage_$(date +%F_%H%M).tgz" -C /data .
```

If `STORAGE_BACKEND=s3`, skip this: enable bucket **versioning** plus a
lifecycle policy and (optionally) cross-region replication instead.

## 3. Consistent point-in-time snapshot

The DB dump and the storage tar are taken at different instants, so a render
that completes between them can leave a row without a file (or vice versa). For
a strictly consistent pair, quiesce writers first:

```bash
$COMPOSE stop backend worker
#   ... run steps 1 and 2 ...
$COMPOSE start backend worker
```

Expect roughly a minute of downtime. `task_acks_late=True` means in-flight
Celery tasks are re-delivered after restart rather than lost.

## 4. Nightly automation

`scripts/` is empty in RC-6 — create the script below and schedule it.

`scripts/backup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./production.env; set +a

COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
DEST="${BACKUP_DIR:-$PWD/backup}"
STAMP="$(date +%F_%H%M)"
mkdir -p "$DEST"

$COMPOSE exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "$DEST/db_$STAMP.sql.gz"

docker run --rm -v hackrootai_storage_data:/data:ro -v "$DEST":/backup busybox \
  tar czf "/backup/storage_$STAMP.tgz" -C /data .

# retention: 30 daily
find "$DEST" -name 'db_*.sql.gz' -mtime +30 -delete
find "$DEST" -name 'storage_*.tgz' -mtime +30 -delete

# off-host copy — REQUIRED (adjust to your object store)
# aws s3 sync "$DEST" s3://hackroot-backups/$(hostname)/ --storage-class STANDARD_IA

echo "backup complete: $STAMP"
```

```bash
chmod +x scripts/backup.sh
# crontab -e  — 02:15 daily
15 2 * * * /opt/hackroot/scripts/backup.sh >> /var/log/hackroot-backup.log 2>&1
```

## 5. Retention policy

| Tier | Frequency | Keep | Storage |
|---|---|---|---|
| Daily | 02:15 nightly | 30 copies | off-host object storage |
| Weekly | Sunday | 12 copies | off-host, separate prefix |
| Monthly | 1st of month | 12 copies | off-host / cold tier |
| Pre-deploy | before every release | 7 most recent | off-host |

Targets: **RPO ≤ 24 h** (nightly dumps), **RTO ≤ 1 h** (see
[RECOVERY.md](RECOVERY.md)).

Rules:

- A dump on the same disk as the database is **not a backup** — always copy
  off-host.
- Keep DB dumps and storage tars from the same run paired; migrations are
  forward-only and video rows reference on-disk paths.
- `production.env` is not in backups (and must never be committed) — store the
  secrets separately in a password manager or secret store, or a restore will
  leave you with an unbootable stack.
- Encrypt backups at rest; dumps contain user emails, bcrypt hashes and billing
  records.
- Restrict `backup/` to `chmod 700`.

## 6. Test your restores

Untested backups are hypotheses. Restore into a scratch stack at least
quarterly and follow the verification steps in
[RECOVERY.md](RECOVERY.md#5-verification).
