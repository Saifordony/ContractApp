"""The single benchmark engine.

Comparison is computed from the contract's grounded analysis (the one extraction
pipeline) against the seeded ``benchmark_standards`` — no second AI pipeline, no
duplicate engine. Gaps reuse the extraction evidence, so benchmark findings are
grounded by construction.
"""
from __future__ import annotations

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.constants import CLAUSE_LABELS, grade_from_score

_IMPORTANCE_WEIGHT = {"high": 3.0, "medium": 2.0, "low": 1.0}
_STATUS_CREDIT = {"found": 1.0, "partially_found": 0.6, "needs_review": 0.3, "not_found": 0.0}


def _recommendation(key: str, status: str, expected: dict) -> str:
    label = CLAUSE_LABELS.get(key, {}).get("en", key)
    typical = expected.get("typical_terms", "")
    if status == "not_found":
        return f"Add a {label} clause. Typical terms: {typical}"
    return f"Strengthen the {label} clause — it is incomplete or unclear. Typical terms: {typical}"


async def find_standard(db: AsyncIOMotorDatabase, contract_type: str, region: str) -> Optional[dict]:
    """Look up the best-matching benchmark standard with sensible fallbacks."""
    for query in (
        {"contract_type": contract_type, "region": region},
        {"contract_type": contract_type},
        {"contract_type": "general", "region": region},
        {"contract_type": "general"},
    ):
        doc = await db.benchmark_standards.find_one(query)
        if doc is not None:
            return doc
    return None


def compare_to_standard(analysis: dict, standard: dict) -> dict:
    """Pure comparison of a grounded analysis against a benchmark standard."""
    clauses_by_key = {c["key"]: c for c in analysis.get("clauses", [])}
    gaps = []
    weighted_total = 0.0
    weighted_earned = 0.0
    confidences: list[float] = []

    for expected in standard.get("clauses", []):
        key = expected["key"]
        importance = expected.get("importance", "medium")
        weight = _IMPORTANCE_WEIGHT.get(importance, 2.0)
        clause = clauses_by_key.get(key)
        status = clause["status"] if clause else "not_found"
        credit = _STATUS_CREDIT.get(status, 0.0)

        weighted_total += weight
        weighted_earned += weight * credit
        if clause is not None:
            confidences.append(float(clause.get("confidence", 0.0)))

        if credit < 1.0:
            severity = importance if status == "not_found" else ("medium" if importance == "high" else "low")
            gaps.append({
                "clause_key": key,
                "importance": importance,
                "benchmark_expectation": expected.get("typical_terms", ""),
                "contract_status": status,
                "severity": severity,
                "recommendation": _recommendation(key, status, expected),
                "evidence": clause.get("evidence", []) if clause else [],
            })

    overall = int(round((weighted_earned / weighted_total) * 100)) if weighted_total else 0
    confidence = round(min(1.0, (sum(confidences) / len(confidences)) if confidences else 0.4), 3)
    return {
        "overall_score": overall,
        "grade": grade_from_score(overall),
        "gaps": gaps,
        "confidence": confidence,
    }
