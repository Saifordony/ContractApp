"""Tests for real PDF/CSV/JSON export."""
from __future__ import annotations

import json

import pytest
from bson import ObjectId

from backend.models.common import utcnow
from tests.fakes import SAMPLE_CONTRACT, FakeLLM


async def _contract_with_analysis(auth_client, db) -> str:
    resp = await auth_client.post(
        "/api/contracts",
        json={"title": "Export Me", "contract_type": "service_agreement", "region": "US", "content": SAMPLE_CONTRACT},
    )
    contract_id = resp.json()["id"]
    # Persist a minimal valid analysis directly.
    await db.contract_analyses.insert_one({
        "contract_id": ObjectId(contract_id),
        "created_by": ObjectId(auth_client.auth_user_id),
        "language": "en", "degraded": False, "model": "llama3.1:8b", "confidence": 0.8,
        "clauses": [{
            "key": "termination", "label": {"en": "Termination", "ar": "الإنهاء"},
            "status": "found", "extracted_text": "thirty (30) days written notice",
            "explanation": "Either side can end the contract with 30 days notice.",
            "evidence": [{"text": "thirty (30) days written notice", "char_start": 0, "char_end": 30, "chunk_id": 0}],
            "confidence": 0.85,
        }],
        "health": {"overall_score": 78, "grade": "C", "confidence": 0.7,
                   "dimensions": [{"key": "clarity", "label": {"en": "Clarity", "ar": "الوضوح"},
                                   "score": 80, "explanation": "Clear.", "evidence": []}]},
        "needs_review_count": 0, "created_at": utcnow(),
    })
    return contract_id


@pytest.fixture
async def auth_user_id(auth_client):
    me = await auth_client.get("/api/auth/me")
    auth_client.auth_user_id = me.json()["id"]  # type: ignore[attr-defined]
    return auth_client.auth_user_id


@pytest.mark.asyncio
async def test_export_pdf_is_a_real_file(auth_client, db, auth_user_id):
    contract_id = await _contract_with_analysis(auth_client, db)
    resp = await auth_client.get(f"/api/contracts/{contract_id}/export/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"  # a genuine PDF, not a stub
    assert len(resp.content) > 800


@pytest.mark.asyncio
async def test_export_json(auth_client, db, auth_user_id):
    contract_id = await _contract_with_analysis(auth_client, db)
    resp = await auth_client.get(f"/api/contracts/{contract_id}/export/json")
    assert resp.status_code == 200
    body = json.loads(resp.content)
    assert body["contract"]["title"] == "Export Me"
    assert body["analysis"]["clauses"][0]["key"] == "termination"


@pytest.mark.asyncio
async def test_export_csv(auth_client, db, auth_user_id):
    contract_id = await _contract_with_analysis(auth_client, db)
    resp = await auth_client.get(f"/api/contracts/{contract_id}/export/csv")
    assert resp.status_code == 200
    text = resp.content.decode("utf-8")
    assert "section,key,label" in text
    assert "termination" in text


@pytest.mark.asyncio
async def test_export_requires_analysis(auth_client, auth_user_id):
    resp = await auth_client.post(
        "/api/contracts", json={"title": "No Analysis", "content": SAMPLE_CONTRACT})
    contract_id = resp.json()["id"]
    pdf = await auth_client.get(f"/api/contracts/{contract_id}/export/pdf")
    assert pdf.status_code == 404
