#!/bin/sh
# P24 — Postgres backup with retention. Run from cron on the server, e.g. daily at 2am:
#   0 2 * * * cd /path/to/ads-command-center && ./scripts/backup.sh >> /var/log/ads-cc-backup.log 2>&1
#
# Usage: ./scripts/backup.sh [backup_dir] [days_to_keep]
set -eu

BACKUP_DIR="${1:-./backups}"
KEEP_DAYS="${2:-14}"
COMPOSE_FILE="docker-compose.prod.yml"
STAMP="$(date +%F_%H%M%S)"
OUT="$BACKUP_DIR/ads_command_center_$STAMP.sql.gz"

mkdir -p "$BACKUP_DIR"
docker compose -f "$COMPOSE_FILE" exec -T postgres pg_dump -U ads ads_command_center | gzip > "$OUT"
echo "Backup written: $OUT ($(du -h "$OUT" | cut -f1))"

find "$BACKUP_DIR" -name "ads_command_center_*.sql.gz" -mtime "+$KEEP_DAYS" -print -delete
