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
