#!/usr/bin/env bash
# Prepare OSRM data for Algeria (docs/ARCHITECTURE.md §2.4).
# Requires ~8-16 GB RAM and ~2-4 GB disk. Run once before `docker compose --profile osrm up osrm`.
set -euo pipefail

DATA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/data"
PBF="algeria-latest.osm.pbf"
OSRM_IMAGE="osrm/osrm-backend:latest"

mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

# 1. Download Algeria OSM extract
if [ ! -f "$PBF" ]; then
  echo "Downloading $PBF ..."
  wget -q "https://download.geofabrik.de/africa/$PBF"
fi

# 2. Extract (car profile), 3. partition (MLD), 4. customize
docker run -t -v "$DATA_DIR:/data" "$OSRM_IMAGE" osrm-extract -p /opt/car.lua "/data/$PBF"
docker run -t -v "$DATA_DIR:/data" "$OSRM_IMAGE" osrm-partition "/data/algeria-latest.osrm"
docker run -t -v "$DATA_DIR:/data" "$OSRM_IMAGE" osrm-customize "/data/algeria-latest.osrm"

echo "OSRM data ready in $DATA_DIR"
