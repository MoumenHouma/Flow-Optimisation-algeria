"""OSRM client tests against a real local HTTP server speaking the /table contract.

The OSRM engine itself needs Docker + the Algeria OSM extract (see infra/osrm),
which can't run here — but this exercises the exact HTTP request/response shape
the worker relies on, so the integration is verified end-to-end at the protocol.
"""

import http.server
import json
import threading

import fakeredis.aioredis
import pytest

from optimizer.distance_matrix import (
    build_distance_matrix,
    build_matrix_with_fallback,
    osrm_healthy,
)
from optimizer.models import GeoPoint

POINTS = [GeoPoint(36.7538, 3.0588), GeoPoint(36.75, 3.06), GeoPoint(36.76, 3.07)]

# A valid OSRM table response with one unroutable pair (null) to exercise backfill.
OSRM_OK = {
    "code": "Ok",
    "durations": [[0, 100, None], [100, 0, 200], [None, 200, 0]],
    "distances": [[0, 1000, None], [1000, 0, 2000], [None, 2000, 0]],
}


class _Handler(http.server.BaseHTTPRequestHandler):
    response: dict = OSRM_OK

    def do_GET(self) -> None:  # noqa: N802
        body = json.dumps(type(self).response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # silence test server logs
        pass


@pytest.fixture(autouse=True)
def _bypass_proxy(monkeypatch):
    # Never route the localhost test server through the agent proxy.
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setenv("no_proxy", "*")


@pytest.fixture
def osrm_server():
    _Handler.response = OSRM_OK
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", _Handler
    server.shutdown()


@pytest.fixture
def redis_client():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


async def test_parses_osrm_table_and_backfills_nulls(osrm_server, redis_client):
    base_url, _ = osrm_server
    matrix = await build_distance_matrix(POINTS, redis_client, osrm_url=base_url)

    # Real OSRM values preserved
    assert matrix.distances[0][1] == 1000
    assert matrix.durations[1][2] == 200
    # Unroutable (null) cells backfilled with a positive great-circle estimate
    assert matrix.distances[0][2] > 0
    assert all(v is not None for row in matrix.distances for v in row)

    # Result is cached in Redis (dm:{hash})
    keys = await redis_client.keys("dm:*")
    assert len(keys) == 1


async def test_fallback_flag_true_with_live_osrm(osrm_server, redis_client):
    base_url, _ = osrm_server
    _matrix, used_osrm = await build_matrix_with_fallback(POINTS, redis_client, osrm_url=base_url)
    assert used_osrm is True


async def test_fallback_on_non_ok_code(osrm_server, redis_client):
    base_url, handler = osrm_server
    handler.response = {"code": "NoTable", "message": "no table"}
    matrix, used_osrm = await build_matrix_with_fallback(POINTS, redis_client, osrm_url=base_url)
    assert used_osrm is False  # haversine fallback
    assert matrix.distances[0][1] > 0


async def test_health_check(osrm_server):
    base_url, _ = osrm_server
    assert await osrm_healthy(base_url) is True
    # An unused port -> unreachable -> False
    assert await osrm_healthy("http://127.0.0.1:1") is False
