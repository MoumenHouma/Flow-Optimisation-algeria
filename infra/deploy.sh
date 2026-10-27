#!/usr/bin/env bash
# RouteOpt — production deploy on a single host (docs/DEPLOYMENT.md §8).
#
# Pulls the latest code, applies DB migrations, (re)builds and starts the prod
# stack, then gates on readiness before returning. Idempotent: safe to re-run.
#
# Prerequisites on the host (one-off):
#   - Docker + Docker Compose plugin
#   - a completed .env (from .env.prod.example) with real secrets
#   - JWT keys in infra/secrets/ and TLS certs in infra/nginx/certs/
#   - OSRM data built once (infra/osrm/prepare.sh) — needs 8-16 GB RAM for Algeria
#
# Usage:  ./infra/deploy.sh [git-ref]      (default: current branch's upstream)
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root

REF="${1:-}"
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/health/ready}"

echo "==> Fetching latest code"
git fetch --all --prune
if [ -n "$REF" ]; then
  git checkout "$REF"
  git pull --ff-only || true
else
  git pull --ff-only
fi

echo "==> Building images"
"${COMPOSE[@]}" build

echo "==> Applying database migrations (alembic upgrade head)"
# Run migrations in a one-off backend container so the API never starts against
# an un-migrated schema.
"${COMPOSE[@]}" run --rm backend alembic upgrade head

echo "==> Starting the stack"
"${COMPOSE[@]}" up -d

echo "==> Waiting for readiness at $HEALTH_URL"
for i in $(seq 1 30); do
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    echo "==> Ready after ${i}0s."
    "${COMPOSE[@]}" ps
    exit 0
  fi
  sleep 10
done

echo "!! Not ready after 5 min — dumping recent logs" >&2
"${COMPOSE[@]}" logs --tail=50 backend optimization-worker gateway >&2
exit 1
