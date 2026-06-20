"""Tests for the single benchmark engine."""
from __future__ import annotations

import pytest
from mongomock_motor import AsyncMongoMockClient

from backend.migrations import seed_benchmark_standards
from backend.services.benchmark import compare_to_standard, find_standard


def _analysis(statuses: dict[str, str]) -> dict:
    clauses = [
        {"key": key, "status": status, "confidence": 0.8,
         "evidence": [{"text": "x", "char_start": 0, "char_end": 1, "chunk_id": 0}] if status == "found" else []}
        for key, status in statuses.items()
    ]
    return {"clauses": clauses, "degraded": False}


def test_compare_full_coverage_scores_high():
    standard = {"clauses": [
        {"key": "termination", "importance": "high", "typical_terms": "30 days notice"},
        {"key": "liability", "importance": "high", "typical_terms": "cap on damages"},
    ]}
    analysis = _analysis({"termination": "found", "liability": "found"})
    result = compare_to_standard(analysis, standard)
    assert result["overall_score"] == 100
    assert result["gaps"] == []
    assert result["grade"] == "A"


def test_compare_missing_clause_produces_gap():
    standard = {"clauses": [
        {"key": "termination", "importance": "high", "typical_terms": "30 days notice"},
        {"key": "indemnification", "importance": "high", "typical_terms": "hold harmless"},
    ]}
    analysis = _analysis({"termination": "found", "indemnification": "not_found"})
    result = compare_to_standard(analysis, standard)
    assert result["overall_score"] < 100
    gap_keys = {g["clause_key"] for g in result["gaps"]}
    assert "indemnification" in gap_keys
    gap = next(g for g in result["gaps"] if g["clause_key"] == "indemnification")
    assert gap["severity"] == "high"
    assert "indemnification" in gap["recommendation"].lower() or "Indemnification" in gap["recommendation"]


@pytest.mark.asyncio
async def test_find_standard_with_fallback():
    db = AsyncMongoMockClient()["t"]
    await seed_benchmark_standards(db)
    # Exact match exists.
    exact = await find_standard(db, "service_agreement", "US")
    assert exact is not None
    assert exact["contract_type"] == "service_agreement"
    # Unknown region falls back to the contract type, then to general.
    fallback = await find_standard(db, "nda", "Atlantis")
    assert fallback is not None
    missing = await find_standard(db, "totally_unknown", "Atlantis")
    assert missing is not None  # falls back to general
    assert missing["contract_type"] == "general"
