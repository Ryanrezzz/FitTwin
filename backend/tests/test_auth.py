"""Auth + profile tests — register/login/refresh/me and profile CRUD over the
real security stack (Argon2 + JWT) with in-memory storage."""
from __future__ import annotations

from tests.conftest import CREDS, PROFILE


def test_register_returns_user_without_hash(client):
    r = client.post("/api/v1/auth/register", json=CREDS)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == CREDS["email"]
    assert body["role"] == "user"
    assert "password_hash" not in body and "password" not in body


def test_duplicate_register_is_conflict(client):
    client.post("/api/v1/auth/register", json=CREDS)
    r = client.post("/api/v1/auth/register", json=CREDS)
    assert r.status_code == 409


def test_login_returns_token_pair(client):
    client.post("/api/v1/auth/register", json=CREDS)
    r = client.post("/api/v1/auth/login", json=CREDS)
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_wrong_password_is_401(client):
    client.post("/api/v1/auth/register", json=CREDS)
    r = client.post("/api/v1/auth/login", json={**CREDS, "password": "wrongpassword"})
    assert r.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    r = client.get("/api/v1/auth/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == CREDS["email"]


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_issues_new_access_token(client):
    client.post("/api/v1/auth/register", json=CREDS)
    tokens = client.post("/api/v1/auth/login", json=CREDS).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_access_token_cannot_be_used_as_refresh(client):
    client.post("/api/v1/auth/register", json=CREDS)
    tokens = client.post("/api/v1/auth/login", json=CREDS).json()
    # access token has type=access; refresh must reject it
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401


def test_profile_upsert_then_get(client, auth_headers):
    put = client.put("/api/v1/profile", json=PROFILE, headers=auth_headers)
    assert put.status_code == 200
    assert put.json()["name"] == "Alex"

    get = client.get("/api/v1/profile", headers=auth_headers)
    assert get.status_code == 200
    assert get.json()["goal"] == "lose"
    assert get.json()["training_days"] == 4


def test_get_profile_before_onboarding_is_404(client, auth_headers):
    assert client.get("/api/v1/profile", headers=auth_headers).status_code == 404


def test_short_password_is_rejected(client):
    r = client.post("/api/v1/auth/register", json={"email": "x@y.com", "password": "short"})
    assert r.status_code == 422
