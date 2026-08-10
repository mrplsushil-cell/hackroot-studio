# Backup & Restore Runbook — Hackroot Studio

This runbook covers backing up and restoring the two stateful components of a
Hackroot Studio deployment: the **PostgreSQL** database and the **media storage**
(`/data/storage` volume containing generated videos, thumbnails, and brand logos).

> All commands assume you are in the project root and use the production compose
> file: `docker compose -f docker-compose.prod.yml --env-file production.env`.

## Backup

### 1. Database (recommended: nightly logical dump)

```bash
mkdir -p backup
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "backup/db_$(date +%F_%H%M).sql.gz"
```
- Retention: keep 30 daily + 12 monthly copies.
- Copy off-host (S3 / object storage / second volume) — a dump on the same disk
  is not a backup.

### 2. Storage (local backend)

```bash
docker run --rm \
  -v hackrootai_storage_data:/data \
  -v "$(pwd)/backup":/backup busybox \
  tar czf "/backup/storage_$(date +%F_%H%M).tgz" -C /data .
```
- If `STORAGE_BACKEND=s3`, enable S3 bucket **versioning** + lifecycle rules
  instead; no volume snapshot needed.

### 3. One-shot full snapshot (stop-the-world, safest)

For a point-in-time guarantee, briefly pause writes:

```bash
docker compose -f docker-compose.prod.yml stop backend worker
# run the DB dump + storage tar above
docker compose -f docker-compose.prod.yml start backend worker
```

## Restore

### Database

```bash
# 1. (Optional) drop + recreate to be safe
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;"

# 2. Restore
gunzip -c "backup/db_2026-08-03_0200.sql.gz" | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" "$POSTGRES_DB"

# 3. Re-run migrations defensively (no-op if already applied)
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Storage

```bash
docker run --rm \
  -v hackrootai_storage_data:/data \
  -v "$(pwd)/backup":/backup busybox \
  tar xzf "/backup/storage_2026-08-03_0200.tgz" -C /data
```

## Verification after restore

```bash
curl -f http://localhost/health                       # backend healthy
docker compose -f docker-compose.prod.yml exec backend \
  python -c "import app.database"                     # imports OK
# Log in via the UI and confirm a previously generated video still downloads.
```

## Notes

- Migrations are forward-only; restoring an older DB dump than the running code
  expects will fail the `alembic upgrade head` check — keep code and DB dumps
  versioned together.
- Never restore storage without also restoring the DB — video rows point at
  `output_path` / `thumbnail_path` on disk.
