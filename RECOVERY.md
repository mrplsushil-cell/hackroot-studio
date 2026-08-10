# RECOVERY

Restore procedures for the Hackroot Studio production stack. Read
[BACKUP.md](BACKUP.md) first — restores assume its artifact layout
(`backup/db_<stamp>.sql.gz`, `backup/storage_<stamp>.tgz`).

```bash
export COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
set -a; . ./production.env; set +a
```

**Always restore the database and the storage volume from the same backup
run.** Video rows carry `output_path` / `thumbnail_path` pointing at files on
the `storage_data` volume; mismatched pairs produce broken media links.

---

## 1. Stop the writers

```bash
$COMPOSE stop backend worker frontend
```

Leave `postgres` and `redis` running — you need Postgres to accept the restore.
Keeping `nginx` up lets it serve a maintenance page if you have one; otherwise
stop it too.

## 2. Restore the database

### From a gzipped plain SQL dump

```bash
# drop and recreate for a clean target
$COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d postgres \
  -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";"
$COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d postgres \
  -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\";"

gunzip -c backup/db_2026-08-03_0215.sql.gz \
  | $COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1
```

If `DROP DATABASE` fails with "is being accessed by other users", terminate
stragglers:

```bash
$COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB';"
```

### From a custom-format dump (`-Fc`)

```bash
$COMPOSE exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --clean --if-exists --no-owner -j 4 < backup/db_2026-08-03_0215.dump
```

### Re-apply migrations defensively

```bash
$COMPOSE run --rm backend alembic upgrade head
$COMPOSE run --rm backend alembic current
```

A no-op if the dump was already at head. If it errors, the dump predates the
running code — see §4.

## 3. Restore the storage volume

Wipe first so deleted-then-restored state does not leave orphans:

```bash
docker run --rm -v hackrootai_storage_data:/data busybox \
  sh -c 'rm -rf /data/* /data/.[!.]* 2>/dev/null; true'

docker run --rm \
  -v hackrootai_storage_data:/data \
  -v "$(pwd)/backup":/backup:ro busybox \
  tar xzf /backup/storage_2026-08-03_0215.tgz -C /data
```

Confirm the volume name first (`docker volume ls --filter name=storage_data`).

To recover a single file without touching the live volume, extract the tar to a
temp dir and copy the one path back in.

With `STORAGE_BACKEND=s3`, restore by rolling the object version back or
re-syncing from the versioned bucket; the volume is unused.

### Rebuilding a lost volume from scratch

If `storage_data` was deleted entirely, `docker compose up -d` recreates it
empty and the backend/worker will populate `/data/storage` on next write
(`main.py` calls `mkdir(parents=True, exist_ok=True)`); pre-existing media stays
missing until a tar is restored.

## 4. Restart and re-check

```bash
$COMPOSE up -d
$COMPOSE ps
$COMPOSE logs --tail=100 backend worker
```

The backend runs `alembic upgrade head` on boot, so a stale dump surfaces here.

## 5. Verification

```bash
# 1. Health through nginx
curl -f http://localhost/health          # {"ok":true,...,"env":"production"}

# 2. Row counts look sane
$COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT (SELECT count(*) FROM users) AS users,
          (SELECT count(*) FROM videos) AS videos;"

# 3. Migration head matches the code
$COMPOSE exec backend alembic current

# 4. Media present on the volume
$COMPOSE exec backend sh -c 'du -sh /data/storage && ls /data/storage | head'

# 5. Worker consumes tasks
$COMPOSE exec redis redis-cli -n 1 llen default    # should drain, not grow
```

Then, manually: log in, open a previously generated video, confirm playback and
download; run one fresh generation end-to-end; confirm credit balance and
invoices on an existing account.

## 6. Point-in-time notes

RC-6 uses **logical dumps only** — recovery granularity equals your dump
interval (nightly ⇒ RPO up to 24 h). There is no WAL archiving in
`docker-compose.prod.yml`; the `postgres` service runs stock
`postgres:16-alpine` with no `archive_command`.

To get true PITR, add to the postgres service:

- `wal_level = replica`, `archive_mode = on`, and an `archive_command` shipping
  WAL segments off-host (or use `pgBackRest` / `wal-g` in a sidecar);
- a base backup schedule (`pg_basebackup`) alongside the WAL archive;
- recovery via `restore_command` + `recovery_target_time`.

Until then:

- **Redis is not recoverable state.** It is AOF-persisted (`--appendonly yes`)
  on `redis_data`, but after a DB restore the safest move is to flush stale
  task/result state: `$COMPOSE exec redis redis-cli -n 1 flushdb` and
  `... -n 2 flushdb`. Re-submit any renders that were in flight.
- **Secrets are not in backups.** `production.env` must be restored from your
  secret store. If `JWT_SECRET` differs from the original, every existing token
  is invalidated and all users must log in again.
- **Rollback of a bad deploy** = redeploy the previous image tag *and* restore
  the pre-deploy dump. Alembic has no downgrade guarantee across releases.

## 7. Disaster recovery on a fresh host

1. Install Docker Engine 24+ / Compose v2.
2. Clone the repo at the released tag.
3. Restore `production.env` from the secret store; `chmod 600`.
4. `docker compose -f docker-compose.prod.yml --env-file production.env up -d postgres redis`
5. Restore the DB (§2) and the storage volume (§3).
6. `docker compose -f docker-compose.prod.yml --env-file production.env up -d --build`
7. Repoint DNS, install TLS certs, uncomment the cert mount + 443 block
   ([DEPLOYMENT.md](DEPLOYMENT.md#5-nginx-and-tls)).
8. Run the §5 verification list.

Target RTO ≤ 1 hour with backups already on the host; add transfer time when
pulling from cold storage.
