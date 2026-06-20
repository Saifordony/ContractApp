"""Test the health endpoint."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["db"] in ("up", "down")
    assert "status" in body
    assert body["ai"]["model"]
    assert "base_url" in body["ai"]
