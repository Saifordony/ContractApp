"""Integration tests for the auth router."""
from __future__ import annotations

import pytest

from tests.helpers import auth_header, register_and_token


@pytest.mark.asyncio
async def test_register_returns_user_and_tokens(client):
    resp = await client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["username"] == "alice"
    assert body["user"]["preferences"] == {"theme": "light", "language": "en"}
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert "hashed_password" not in body["user"]


@pytest.mark.asyncio
async def test_duplicate_username_and_email_rejected(client):
    await register_and_token(client, "bob", "bob@example.com")
    dup_user = await client.post(
        "/api/auth/register",
        json={"username": "bob", "email": "other@example.com", "password": "password123"},
    )
    assert dup_user.status_code == 409
    assert dup_user.json()["code"] == "username_taken"

    dup_email = await client.post(
        "/api/auth/register",
        json={"username": "bob2", "email": "bob@example.com", "password": "password123"},
    )
    assert dup_email.status_code == 409
    assert dup_email.json()["code"] == "email_taken"


@pytest.mark.asyncio
async def test_login_success_and_failure(client):
    await register_and_token(client, "carol", "carol@example.com")

    ok = await client.post("/api/auth/login", json={"username": "carol", "password": "password123"})
    assert ok.status_code == 200
    assert ok.json()["tokens"]["access_token"]

    bad = await client.post("/api/auth/login", json={"username": "carol", "password": "nope"})
    assert bad.status_code == 401
    assert bad.json()["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_login_rate_limited_after_max_attempts(client):
    await register_and_token(client, "dave", "dave@example.com")
    # Default limit is 5 failed attempts within the window.
    for _ in range(5):
        r = await client.post("/api/auth/login", json={"username": "dave", "password": "wrong"})
        assert r.status_code == 401
    blocked = await client.post("/api/auth/login", json={"username": "dave", "password": "wrong"})
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "rate_limited"


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    unauth = await client.get("/api/auth/me")
    assert unauth.status_code == 401

    data = await register_and_token(client, "erin", "erin@example.com")
    me = await client.get("/api/auth/me", headers=auth_header(data["tokens"]["access_token"]))
    assert me.status_code == 200
    assert me.json()["username"] == "erin"


@pytest.mark.asyncio
async def test_refresh_rotates_and_revokes_old_token(client):
    data = await register_and_token(client, "frank", "frank@example.com")
    old_refresh = data["tokens"]["refresh_token"]

    rotated = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]
    assert new_refresh != old_refresh

    # The old refresh token must no longer work after rotation.
    reused = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client):
    data = await register_and_token(client, "grace", "grace@example.com")
    refresh = data["tokens"]["refresh_token"]

    logout = await client.post("/api/auth/logout", json={"refresh_token": refresh})
    assert logout.status_code == 204

    after = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_preferences_persist_server_side(client):
    data = await register_and_token(client, "heidi", "heidi@example.com")
    headers = auth_header(data["tokens"]["access_token"])

    updated = await client.patch("/api/auth/me/preferences", json={"theme": "dark", "language": "ar"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["preferences"] == {"theme": "dark", "language": "ar"}

    # A fresh read reflects the persisted change.
    me = await client.get("/api/auth/me", headers=headers)
    assert me.json()["preferences"]["theme"] == "dark"


@pytest.mark.asyncio
async def test_password_reset_flow(client):
    await register_and_token(client, "ivan", "ivan@example.com")

    request = await client.post("/api/auth/password-reset/request", json={"email": "ivan@example.com"})
    assert request.status_code == 202
    token = request.json()["reset_token"]
    assert token

    confirm = await client.post(
        "/api/auth/password-reset/confirm", json={"token": token, "new_password": "newpassword456"}
    )
    assert confirm.status_code == 204

    old_login = await client.post("/api/auth/login", json={"username": "ivan", "password": "password123"})
    assert old_login.status_code == 401
    new_login = await client.post("/api/auth/login", json={"username": "ivan", "password": "newpassword456"})
    assert new_login.status_code == 200


@pytest.mark.asyncio
async def test_password_reset_request_unknown_email_is_generic(client):
    resp = await client.post("/api/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert resp.status_code == 202
    assert resp.json().get("reset_token") is None
