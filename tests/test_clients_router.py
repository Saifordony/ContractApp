"""Integration tests for client CRUD and ownership scoping."""
from __future__ import annotations

import pytest

from tests.helpers import auth_header, register_and_token


@pytest.mark.asyncio
async def test_client_crud(auth_client):
    created = await auth_client.post("/api/clients", json={"name": "Acme Corp", "email": "legal@acme.com"})
    assert created.status_code == 201, created.text
    client_id = created.json()["id"]
    assert created.json()["name"] == "Acme Corp"

    fetched = await auth_client.get(f"/api/clients/{client_id}")
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "legal@acme.com"

    updated = await auth_client.patch(f"/api/clients/{client_id}", json={"company": "Acme Inc"})
    assert updated.status_code == 200
    assert updated.json()["company"] == "Acme Inc"

    listing = await auth_client.get("/api/clients")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    deleted = await auth_client.delete(f"/api/clients/{client_id}")
    assert deleted.status_code == 204
    gone = await auth_client.get(f"/api/clients/{client_id}")
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_client_search(auth_client):
    await auth_client.post("/api/clients", json={"name": "Northwind Traders"})
    await auth_client.post("/api/clients", json={"name": "Globex"})
    result = await auth_client.get("/api/clients", params={"search": "north"})
    assert result.status_code == 200
    assert result.json()["total"] == 1
    assert result.json()["items"][0]["name"] == "Northwind Traders"


@pytest.mark.asyncio
async def test_clients_scoped_to_owner(client):
    owner = await register_and_token(client, "owner", "owner@example.com")
    other = await register_and_token(client, "intruder", "intruder@example.com")

    created = await client.post(
        "/api/clients", json={"name": "Private Client"}, headers=auth_header(owner["tokens"]["access_token"])
    )
    client_id = created.json()["id"]

    # The other user must not see or fetch it.
    intruder_headers = auth_header(other["tokens"]["access_token"])
    listing = await client.get("/api/clients", headers=intruder_headers)
    assert listing.json()["total"] == 0
    fetch = await client.get(f"/api/clients/{client_id}", headers=intruder_headers)
    assert fetch.status_code == 404
