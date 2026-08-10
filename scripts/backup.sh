#!/usr/bin/env bash
# =============================================================================
# Hackroot Studio — production backup
# =============================================================================
# Backs up:
#   * PostgreSQL database  -> backup/db_<stamp>.sql.gz   (includes brand_kit
#                             and template tables, plus all user data)
#   * Rendered media + uploaded assets (storage_data volume)
#                          -> backup/storage_<stamp>.tgz  (covers brand-kit
#                             logos, product images, generated MP4s/thumbnails)
#
# Brand Kits and Templates are fully covered by the DB dump + the storage
# tarball (logos are files on the storage volume). Restoring both from the
# SAME backup run keeps video paths consistent.
#
# Usage:
#   ./scripts/backup.sh            # uses production.env in repo root
#   RETENTION_DAYS=30 ./scripts/backup.sh
# =============================================================================
set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
STAMP="$(date +%Y%m%d_%H%M%S)"
DEST="${BACKUP_DIR:-./backup}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$DEST/db" "$DEST/storage"

echo "[backup] starting $STAMP"

# --- 1. Database (logical dump, compressed) ---
echo "[backup] postgres -> db_$STAMP.sql.gz"
$COMPOSE exec -T postgres \
  pg_dump --username="$POSTGRES_USER" --no-owner --clean --if-exists "$POSTGRES_DB" \
  | gzip > "$DEST/db/db_$STAMP.sql.gz"
echo "[backup] db size: $(du -h "$DEST/db/db_$STAMP.sql.gz" | cut -f1)"

# --- 2. Storage volume (media, brand-kit logos, templates assets) ---
echo "[backup] storage -> storage_$STAMP.tgz"
# Resolve the real volume name (compose prefixes it with the project name).
VOL="$($COMPOSE config --volumes | grep -E '^storage_data' || true)"
VOL="${VOL:-storage_data}"
FULL_VOL="$VOL"
if [ "$VOL" = "storage_data" ]; then
  PROJECT="$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '_')"
  FULL_VOL="${PROJECT}_storage_data"
fi
docker run --rm -v "$FULL_VOL":/data -v "$PWD/$DEST/storage":/out busybox \
  tar czf "/out/storage_$STAMP.tgz" -C /data .
echo "[backup] storage size: $(du -h "$DEST/storage/storage_$STAMP.tgz" | cut -f1)"

# --- 3. Prune old backups ---
echo "[backup] pruning older than $RETENTION_DAYS days"
find "$DEST/db" -name 'db_*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
find "$DEST/storage" -name 'storage_*.tgz' -mtime +"$RETENTION_DAYS" -delete

echo "[backup] done. Artifacts in $DEST"
