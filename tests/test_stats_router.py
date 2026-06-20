"""Tests for the server-side stats aggregation."""
from __future__ import annotations

import pytest

from tests.fakes import SAMPLE_CONTRACT, FakeLLM


@pytest.fixture
def patch_llm(monkeypatch):
    from backend.services import ai_pipeline
    monkeypatch.setattr(ai_pipeline, "get_llm_client", lambda: FakeLLM())


@pytest.mark.asyncio
async def test_stats_summary_aggregates_server_side(auth_client, patch_llm):
    for i in range(2):
        resp = await auth_client.post(
            "/api/contracts",
            json={"title": f"C{i}", "contract_type": "service_agreement", "content": SAMPLE_CONTRACT},
        )
        await auth_client.post(f"/api/contracts/{resp.json()['id']}/analyze")
    # A third contract left un-analyzed.
    await auth_client.post("/api/contracts", json={"title": "Unanalyzed", "content": SAMPLE_CONTRACT})

    summary = await auth_client.get("/api/stats/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["contracts_total"] == 3
    assert data["analyzed_total"] == 2
    assert data["avg_health_score"] == 78.0  # FakeLLM health overall_score
    assert isinstance(data["high_risk"], list)
    assert isinstance(data["recent_findings"], list)
    assert len(data["recent_findings"]) == 2
    assert isinstance(data["outstanding_reviews"], int)


@pytest.mark.asyncio
async def test_stats_summary_empty(auth_client):
    data = (await auth_client.get("/api/stats/summary")).json()
    assert data["contracts_total"] == 0
    assert data["avg_health_score"] is None
    assert data["high_risk"] == []
