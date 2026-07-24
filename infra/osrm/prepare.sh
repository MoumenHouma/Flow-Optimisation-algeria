#!/usr/bin/env bash
# Prepare OSRM data (docs/ARCHITECTURE.md §2.4). Requires Docker + ~8-16 GB RAM
# and ~2-4 GB disk for Algeria. Run once, then: docker compose --profile osrm up osrm
#
# Defaults to the whole of Algeria. Override for a smaller/faster test region, e.g.:
#   REGION=monaco CONTINENT=europe ./prepare.sh
#   REGION=algeria CONTINENT=africa ./prepare.sh   # (default)
#
# The resulting <region>-latest.osrm is what osrm-routed serves; set OSRM_FILE in
# your .env to match if you change REGION (default: algeria-latest.osrm).
set -euo pipefail

REGION="${REGION:-algeria}"
CONTINENT="${CONTINENT:-africa}"
OSRM_PROFILE="${OSRM_PROFILE:-/opt/car.lua}"
OSRM_IMAGE="${OSRM_IMAGE:-osrm/osrm-backend:latest}"

DATA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/data"
PBF="${REGION}-latest.osm.pbf"
BASE="${REGION}-latest.osrm"

mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

if [ ! -f "$PBF" ]; then
  echo "Downloading $PBF ..."
  curl -fSL -o "$PBF" "https://download.geofabrik.de/${CONTINENT}/${PBF}"
fi

run_osrm() { docker run --rm -t -v "$DATA_DIR:/data" "$OSRM_IMAGE" "$@"; }

echo "1/3 extract (MLD, profile $OSRM_PROFILE)"
run_osrm osrm-extract -p "$OSRM_PROFILE" "/data/$PBF"
echo "2/3 partition"
run_osrm osrm-partition "/data/$BASE"
echo "3/3 customize"
run_osrm osrm-customize "/data/$BASE"

echo
echo "OSRM data ready: $DATA_DIR/$BASE"
echo "Set OSRM_FILE=$BASE in .env, then: docker compose --profile osrm up osrm"
