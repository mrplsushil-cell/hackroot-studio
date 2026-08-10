#!/usr/bin/env bash
# =============================================================================
# Hackroot Studio — production restore
# =============================================================================
# Restores the database and the storage volume from a backup run.
# ALWAYS restore DB + storage from the SAME stamp (video rows reference files
# on the storage volume by path).
#
# Usage:
#   ./scripts/restore.sh <STAMP>           # e.g. ./scripts/restore.sh 20260803_101500
#   DB_ONLY=1 ./scripts/restore.sh <STAMP> # database only
#   STORAGE_ONLY=1 ./scripts/restore.sh <STAMP>
# =============================================================================
set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
STAMP="${1:-}"
if [ -z "$STAMP" ]; then
  echo "usage: $0 <STAMP>" >&2
  exit 1
fi
DEST="${BACKUP_DIR:-./backup}"
DB_FILE="$DEST/db/db_$STAMP.sql.gz"
STORAGE_FILE="$DEST/storage/storage_$STAMP.tgz"

if [ -z "${DB_ONLY:-}" ] && [ ! -f "$STORAGE_FILE" ]; then
  echo "[restore] missing storage backup: $STORAGE_FILE" >&2; exit 1
fi
if [ -z "${STORAGE_ONLY:-}" ] && [ ! -f "$DB_FILE" ]; then
  echo "[restore] missing db backup: $DB_FILE" >&2; exit 1
fi

# Stop the writers so we don't restore under live traffic.
echo "[restore] stopping backend + worker (writers)"
$COMPOSE stop backend worker || true

# --- Database ---
if [ -z "${STORAGE_ONLY:-}" ]; then
  echo "[restore] dropping + recreating $POSTGRES_DB"
  $COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS \"$POSTGRES_DB\";"
  $COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -c "CREATE DATABASE \"$POSTGRES_DB\";"
  echo "[restore] loading db_$STAMP.sql.gz"
  gunzip -c "$DB_FILE" | $COMPOSE exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
fi

# --- Storage volume ---
if [ -z "${DB_ONLY:-}" ]; then
  VOL="storage_data"
  PROJECT="$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '_')"
  FULL_VOL="${PROJECT}_storage_data"
  echo "[restore] extracting storage_$STAMP.tgz into $FULL_VOL"
  docker run --rm -v "$FULL_VOL":/data -v "$PWD/$DEST/storage":/out busybox \
    tar xzf "/out/storage_$STAMP.tgz" -C /data
fi

echo "[restore] restarting services"
$COMPOSE start backend worker
echo "[restore] done. Verify with: docker compose -f docker-compose.prod.yml --env-file production.env ps"
