# Infrastructure

| Path | Purpose |
|---|---|
| `osrm/prepare.sh` | One-time OSRM data prep for Algeria (docs/ARCHITECTURE.md §2.4) |
| `osrm/data/` | Generated `.osrm` files (git-ignored) |
| `nginx/` | Reverse proxy / API gateway config (Kong/Nginx — ARCHITECTURE §2.1) |

The full local stack is orchestrated by the root [`docker-compose.yml`](../docker-compose.yml).
