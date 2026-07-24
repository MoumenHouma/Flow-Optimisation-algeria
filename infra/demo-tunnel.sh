#!/usr/bin/env bash
# RouteOpt — expose a locally-running instance over a temporary public HTTPS URL
# for a live demo, without a VPS or a domain (docs/DEPLOYMENT.md §10, gap A1).
#
# Uses a Cloudflare quick tunnel: no account, no DNS. The URL is EPHEMERAL — it
# changes every run and dies when you Ctrl-C. Do NOT put it in a cold email; it
# is for a booked, live demo you drive in real time. For a stable address, use a
# named tunnel with your own domain (cloudflared tunnel create ...).
#
# Point it at whatever is already serving locally:
#   ./infra/demo-tunnel.sh 80      # the prod-parity gateway (recommended)
#   ./infra/demo-tunnel.sh 5173    # the Vite dev frontend
#
# For the SPA to reach its own API through the tunnel, it must call a same-origin
# relative /api — build the frontend with an empty VITE_API_BASE_URL, and set
# ALLOWED_ORIGINS / PUBLIC_BASE_URL to the tunnel hostname once you know it.
set -euo pipefail

PORT="${1:-80}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found. Install it: winget install Cloudflare.cloudflared" >&2
  exit 1
fi

if ! curl -fsS "http://127.0.0.1:${PORT}" >/dev/null 2>&1 \
  && ! curl -fskS "https://127.0.0.1:${PORT}" >/dev/null 2>&1; then
  echo "Nothing answering on port ${PORT}. Start the stack first, e.g.:" >&2
  echo "  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d" >&2
  exit 1
fi

echo "==> Opening a temporary public tunnel to http://localhost:${PORT}"
echo "    (the trycloudflare.com URL below is temporary — for a live demo only)"
exec cloudflared tunnel --url "http://localhost:${PORT}"
