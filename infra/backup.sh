#!/usr/bin/env bash
# RouteOpt — nightly Postgres backup (docs/DEPLOYMENT.md §9, gap B4).
#
# Dumps the database and, if S3 settings are present, pushes the dump to the
# bucket. Meant to run from cron on the host:
#
#   0 2 * * *  /opt/routeopt/infra/backup.sh >> /var/log/routeopt-backup.log 2>&1
#
# A backup you have never restored is not a backup — test a restore periodically
# (see the restore note in docs/DEPLOYMENT.md §9).
set -euo pipefail

cd "$(dirname "$0")/.."

# Load .env so DB_URL / S3_* are available (ignore comments/blank lines).
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . <(grep -E '^[A-Z_]+=' .env)
  set +a
fi

: "${DB_URL:?DB_URL must be set}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${BACKUP_DIR:-/var/backups/routeopt}"
OUT="${OUT_DIR}/routeopt-${STAMP}.sql.gz"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

mkdir -p "$OUT_DIR"

# asyncpg URL (postgresql+asyncpg://) -> libpq URL (postgresql://) for pg_dump.
PG_URL="${DB_URL/+asyncpg/}"

echo "==> Dumping database to $OUT"
pg_dump "$PG_URL" | gzip > "$OUT"
echo "==> Dump size: $(du -h "$OUT" | cut -f1)"

if [ -n "${S3_BUCKET:-}" ] && command -v aws >/dev/null 2>&1; then
  DEST="s3://${S3_BUCKET}/backups/routeopt-${STAMP}.sql.gz"
  echo "==> Uploading to $DEST"
  ENDPOINT_ARG=()
  [ -n "${S3_ENDPOINT:-}" ] && ENDPOINT_ARG=(--endpoint-url "$S3_ENDPOINT")
  aws "${ENDPOINT_ARG[@]}" s3 cp "$OUT" "$DEST"
else
  echo "==> S3 not configured (or aws CLI absent) — keeping local copy only"
fi

echo "==> Pruning local dumps older than ${RETENTION_DAYS} days"
find "$OUT_DIR" -name 'routeopt-*.sql.gz' -mtime "+${RETENTION_DAYS}" -delete

echo "==> Backup done: $OUT"
