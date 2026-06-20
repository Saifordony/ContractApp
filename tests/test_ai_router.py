"""Integration tests for the streaming AI router (LLM mocked)."""
from __future__ import annotations

import pytest

from backend.migrations import seed_benchmark_standards
from tests.fakes import SAMPLE_CONTRACT, FailingLLM, FakeLLM, parse_sse


@pytest.fixture
def patch_llm(monkeypatch):
    from backend.services import ai_pipeline
    monkeypatch.setattr(ai_pipeline, "get_llm_client", lambda: FakeLLM())


async def _make_contract(auth_client) -> str:
    resp = await auth_client.post(
        "/api/contracts",
        json={"title": "MSA", "contract_type": "service_agreement", "region": "US", "content": SAMPLE_CONTRACT},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_analyze_streams_and_persists(auth_client, patch_llm):
    contract_id = await _make_contract(auth_client)
    resp = await auth_client.post(f"/api/contracts/{contract_id}/analyze")
    assert resp.status_code == 200
    events = parse_sse(resp.text)

    types = [t for t, _ in events]
    assert "status" in types  # progress was streamed
    assert types[-1] == "done"
    result = next(data for t, data in events if t == "result")
    assert result["degraded"] is False
    assert len(result["clauses"]) == 10
    assert result["health"]["overall_score"] == 78
    assert result["id"]

    # Persisted and retrievable.
    fetched = await auth_client.get(f"/api/contracts/{contract_id}/analysis")
    assert fetched.status_code == 200
    assert fetched.json()["health"]["grade"] == "C"

    # Contract status flips to analyzed.
    contract = await auth_client.get(f"/api/contracts/{contract_id}")
    assert contract.json()["status"] == "analyzed"


@pytest.mark.asyncio
async def test_analyze_degraded_when_llm_down(auth_client, monkeypatch):
    from backend.services import ai_pipeline
    monkeypatch.setattr(ai_pipeline, "get_llm_client", lambda: FailingLLM())

    contract_id = await _make_contract(auth_client)
    resp = await auth_client.post(f"/api/contracts/{contract_id}/analyze")
    result = next(data for t, data in parse_sse(resp.text) if t == "result")
    assert result["degraded"] is True
    assert result["model"] == "deterministic-fallback"


@pytest.mark.asyncio
async def test_chat_streams_tokens_and_persists(auth_client, patch_llm):
    contract_id = await _make_contract(auth_client)
    resp = await auth_client.post(f"/api/contracts/{contract_id}/chat", json={"question": "How do I terminate?"})
    assert resp.status_code == 200
    events = parse_sse(resp.text)

    assert any(t == "token" for t, _ in events)
    result = next(data for t, data in events if t == "result")
    assert result["citations"], "chat answer must be grounded with citations"

    history = await auth_client.get(f"/api/contracts/{contract_id}/chat")
    roles = [m["role"] for m in history.json()]
    assert roles == ["user", "assistant"]


@pytest.mark.asyncio
async def test_benchmark_auto_analyzes_and_scores(auth_client, db, patch_llm):
    await seed_benchmark_standards(db)
    contract_id = await _make_contract(auth_client)

    resp = await auth_client.post(f"/api/contracts/{contract_id}/benchmark")
    assert resp.status_code == 200
    events = parse_sse(resp.text)
    result = next(data for t, data in events if t == "result")
    assert "overall_score" in result
    assert "gaps" in result
    assert result["grade"]

    fetched = await auth_client.get(f"/api/contracts/{contract_id}/benchmark")
    assert fetched.status_code == 200


@pytest.mark.asyncio
async def test_analysis_404_before_running(auth_client):
    contract_id = await _make_contract(auth_client)
    resp = await auth_client.get(f"/api/contracts/{contract_id}/analysis")
    assert resp.status_code == 404
