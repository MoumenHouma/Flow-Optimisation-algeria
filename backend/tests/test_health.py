"""Smoke test for the health endpoint (no DB/Redis required)."""

from fastapi.testclient import TestClient

from routeopt.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_optimize_requires_auth() -> None:
    response = client.post("/api/v1/routes/optimize", json={})
    assert response.status_code in (401, 422)


def test_readiness_reports_components() -> None:
    # Without live deps this returns 503, but always reports each component.
    response = client.get("/health/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert set(body["components"]) == {"database", "redis", "osrm"}
