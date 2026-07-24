"""Auth endpoint wiring + request validation (no DB required).

These assert the routes exist and Pydantic validation rejects bad input before
any DB access happens.
"""

from fastapi.testclient import TestClient

from routeopt.main import app

client = TestClient(app)


def test_register_rejects_short_password() -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "khaled@acme.dz",
            "password": "short",  # < 8 chars
            "full_name": "Khaled",
        },
    )
    assert resp.status_code == 422


def test_register_rejects_bad_email() -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "not-an-email",
            "password": "longenough",
            "full_name": "Khaled",
        },
    )
    assert resp.status_code == 422


def test_login_requires_fields() -> None:
    resp = client.post("/api/v1/auth/login", json={"email": "khaled@acme.dz"})
    assert resp.status_code == 422


def test_me_requires_bearer_token() -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
