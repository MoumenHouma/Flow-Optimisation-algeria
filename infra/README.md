# Infrastructure

| Path | Purpose |
|---|---|
| `osrm/prepare.sh` | One-time OSRM data prep for Algeria (docs/ARCHITECTURE.md §2.4) |
| `osrm/data/` | Generated `.osrm` files (git-ignored) |
| `nginx/nginx.conf` | Production reverse proxy — TLS termination, upstreams, upload limit |
| `nginx/conf.d/routeopt.conf` | Server blocks: HTTP→HTTPS, `/api/`→backend, rest→frontend |
| `nginx/certs/` | TLS certs `fullchain.pem` / `privkey.pem` (git-ignored, host-provided) |
| `secrets/` | JWT signing keys mounted as Docker secrets (git-ignored) |

- Local stack: [`docker-compose.yml`](../docker-compose.yml).
- Production: `docker-compose.yml` + [`docker-compose.prod.yml`](../docker-compose.prod.yml)
  (see [`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md)).
