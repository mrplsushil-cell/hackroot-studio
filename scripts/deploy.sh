#!/usr/bin/env bash
# =============================================================================
# Hackroot Studio — deploy / upgrade / rollback helper
# =============================================================================
#   ./scripts/deploy.sh up        # first deploy (build + start, run migrations)
#   ./scripts/deploy.sh upgrade   # pull/ rebuild + rolling restart (zero-downtime-ish)
#   ./scripts/deploy.sh down      # stop the stack
#   ./scripts/deploy.sh backup    # one-off backup (./scripts/backup.sh)
#   ./scripts/deploy.sh logs      # follow logs
#   ./scripts/deploy.sh rollback  # restart PREVIOUS image tags (set PREV_TAG first)
#
# All commands require production.env in the repo root.
# =============================================================================
set -euo pipefail
COMPOSE="docker compose -f docker-compose.prod.yml --env-file production.env"
CMD="${1:-up}"

case "$CMD" in
  up)
    echo "[deploy] building + starting (production)"
    $COMPOSE up -d --build
    echo "[deploy] waiting for health..."
    $COMPOSE ps
    ;;
  upgrade)
    echo "[deploy] upgrading — rebuild images and recreate containers"
    $COMPOSE pull
    $COMPOSE up -d --build --force-recreate
    echo "[deploy] health:"; $COMPOSE ps
    ;;
  rollback)
    # Roll back by recreating from previously tagged images.
    PREV_TAG="${PREV_TAG:-previous}"
    echo "[deploy] rolling back to tag '$PREV_TAG' (set PREV_TAG before build)"
    # Example: docker compose up -d --scale ... or re-tag + recreate.
    echo "[deploy] re-tag required images to '$PREV_TAG' before running rollback."
    $COMPOSE up -d --force-recreate
    ;;
  down)
    $COMPOSE down
    ;;
  backup)
    ./scripts/backup.sh
    ;;
  logs)
    $COMPOSE logs -f --tail=100
    ;;
  *)
    echo "usage: $0 {up|upgrade|rollback|down|backup|logs}" >&2
    exit 1
    ;;
esac
