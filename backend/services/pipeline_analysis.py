"""Simple pipeline analysis implementation."""

from __future__ import annotations

from typing import Any, Dict, List


def analyze_pipeline(
    opportunities: List[Dict[str, Any]], stage_probabilities: Dict[str, float] | None = None
) -> Dict[str, Any]:
    probs = stage_probabilities or {
        "prospecting": 0.1,
        "qualification": 0.25,
        "proposal": 0.5,
        "negotiation": 0.75,
        "closed_won": 1.0,
        "closed_lost": 0.0,
    }

    total_pipeline = 0.0
    weighted_pipeline = 0.0
    by_stage: Dict[str, Dict[str, Any]] = {}

    for op in opportunities or []:
        stage = str(op.get("stage", "prospecting")).strip().lower()
        value = float(op.get("value", 0) or 0)
        p = float(probs.get(stage, 0.2))

        total_pipeline += value
        weighted_pipeline += value * p

        rec = by_stage.setdefault(stage, {"count": 0, "value": 0.0, "weighted_value": 0.0})
        rec["count"] += 1
        rec["value"] += value
        rec["weighted_value"] += value * p

    return {
        "opportunities_count": len(opportunities or []),
        "total_pipeline": round(total_pipeline, 2),
        "weighted_pipeline": round(weighted_pipeline, 2),
        "stage_breakdown": by_stage,
        "stage_probabilities": probs,
    }
