"""Dashboard KPI summary endpoint."""

from typing import Dict, Optional

from fastapi import APIRouter, Depends

from backend import main as _main

router = APIRouter()


@router.get("/stats/summary")
async def stats_summary(current_user: dict = Depends(_main.get_current_user)):
    """Dashboard KPIs for the authenticated user, computed from saved analyses.

    Returns total contracts analysed, last analysis date, average health score,
    a high/medium/low health distribution, the most common missing clause, and a
    breakdown of contracts by detected type.
    """
    analyses = await _main.db.contract_analyses.find(
        {"created_by": current_user["username"]}
    ).sort("created_at", -1).to_list(1000)

    scores: list[float] = []
    distribution = {"high": 0, "medium": 0, "low": 0}
    missing_counter: Dict[str, int] = {}
    type_counter: Dict[str, int] = {}
    last_analysis_date: Optional[str] = None

    for analysis in analyses:
        if last_analysis_date is None and analysis.get("created_at"):
            created = analysis["created_at"]
            last_analysis_date = created.isoformat() if hasattr(created, "isoformat") else str(created)
        results = analysis.get("results", {}) if isinstance(analysis, dict) else {}
        health = results.get("health_evaluation", {}) if isinstance(results, dict) else {}

        score = health.get("health_score")
        bucket = _main._score_bucket(score)
        if bucket:
            scores.append(float(score))
            distribution[bucket] += 1

        contract_type = health.get("contract_type") or results.get("contract_type")
        if contract_type:
            type_counter[str(contract_type)] = type_counter.get(str(contract_type), 0) + 1

        for clause in health.get("missing_critical_clauses", []) or []:
            missing_counter[str(clause)] = missing_counter.get(str(clause), 0) + 1

    average_health_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    most_common_missing_clause = (
        max(missing_counter, key=missing_counter.get) if missing_counter else ""
    )

    return {
        "total_contracts": len(analyses),
        "last_analysis_date": last_analysis_date,
        "average_health_score": average_health_score,
        "health_distribution": distribution,
        "most_common_missing_clause": most_common_missing_clause,
        "contracts_by_type": type_counter,
    }
