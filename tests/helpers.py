"""Test helper utilities."""
from __future__ import annotations

from httpx import AsyncClient


async def register_and_token(
    client: AsyncClient,
    username: str = "user",
    email: str | None = None,
    password: str = "password123",
) -> dict:
    email = email or f"{username}@example.com"
    resp = await client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
