"""Integration tests for contract CRUD, upload, filtering, and cascade delete."""
from __future__ import annotations

import pytest

from tests.helpers import auth_header, register_and_token

SAMPLE = (
    "This Service Agreement is made between the parties. "
    "Termination: either party may terminate on 30 days notice. "
    "Confidentiality obligations survive for three years."
)


@pytest.mark.asyncio
async def test_create_text_contract_detects_language(auth_client):
    resp = await auth_client.post(
        "/api/contracts",
        json={"title": "MSA", "contract_type": "service_agreement", "region": "US", "content": SAMPLE},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "MSA"
    assert body["language"] == "en"
    assert body["source_format"] == "text"
    assert body["status"] == "uploaded"


@pytest.mark.asyncio
async def test_create_arabic_contract_detects_language(auth_client):
    arabic = "هذا العقد بين الطرفين. الإنهاء يكون بإشعار خطي قبل ثلاثين يوماً. تسري السرية لمدة ثلاث سنوات."
    resp = await auth_client.post("/api/contracts", json={"title": "عقد", "content": arabic})
    assert resp.status_code == 201
    assert resp.json()["language"] == "ar"


@pytest.mark.asyncio
async def test_upload_text_file(auth_client):
    files = {"file": ("contract.txt", SAMPLE.encode("utf-8"), "text/plain")}
    resp = await auth_client.post("/api/contracts/upload", files=files, data={"contract_type": "service_agreement"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["source_format"] == "text"
    assert "Termination" in resp.json()["content"]


@pytest.mark.asyncio
async def test_contract_list_and_filter(auth_client):
    await auth_client.post("/api/contracts", json={"title": "NDA One", "contract_type": "nda", "content": SAMPLE})
    await auth_client.post("/api/contracts", json={"title": "Lease Two", "contract_type": "lease", "content": SAMPLE})

    all_items = await auth_client.get("/api/contracts")
    assert all_items.json()["total"] == 2

    filtered = await auth_client.get("/api/contracts", params={"contract_type": "nda"})
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["title"] == "NDA One"
    # List items omit the heavy content field.
    assert "content" not in filtered.json()["items"][0]

    searched = await auth_client.get("/api/contracts", params={"search": "lease"})
    assert searched.json()["total"] == 1


@pytest.mark.asyncio
async def test_contract_with_invalid_client_rejected(auth_client):
    resp = await auth_client.post(
        "/api/contracts",
        json={"title": "X", "content": SAMPLE, "client_id": "507f1f77bcf86cd799439011"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "invalid_client"


@pytest.mark.asyncio
async def test_contract_links_real_client_objectid(auth_client):
    client_resp = await auth_client.post("/api/clients", json={"name": "Linked Co"})
    client_id = client_resp.json()["id"]
    contract = await auth_client.post(
        "/api/contracts", json={"title": "Linked", "content": SAMPLE, "client_id": client_id}
    )
    assert contract.status_code == 201
    assert contract.json()["client_id"] == client_id


@pytest.mark.asyncio
async def test_delete_contract_cascades(auth_client, db):
    from bson import ObjectId

    created = await auth_client.post("/api/contracts", json={"title": "ToDelete", "content": SAMPLE})
    contract_id = created.json()["id"]
    # Seed dependent docs directly.
    oid = ObjectId(contract_id)
    await db.contract_analyses.insert_one({"contract_id": oid, "marker": True})
    await db.chat_messages.insert_one({"contract_id": oid, "marker": True})

    deleted = await auth_client.delete(f"/api/contracts/{contract_id}")
    assert deleted.status_code == 204
    assert await db.contract_analyses.count_documents({"contract_id": oid}) == 0
    assert await db.chat_messages.count_documents({"contract_id": oid}) == 0


@pytest.mark.asyncio
async def test_contracts_scoped_to_owner(client):
    owner = await register_and_token(client, "co_owner", "co@example.com")
    other = await register_and_token(client, "co_other", "co2@example.com")
    created = await client.post(
        "/api/contracts", json={"title": "Secret", "content": SAMPLE},
        headers=auth_header(owner["tokens"]["access_token"]),
    )
    contract_id = created.json()["id"]
    fetch = await client.get(
        f"/api/contracts/{contract_id}", headers=auth_header(other["tokens"]["access_token"])
    )
    assert fetch.status_code == 404
