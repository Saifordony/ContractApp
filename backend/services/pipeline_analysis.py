from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

DEFAULT_STAGE_PROBABILITIES = {
    "prospecting": 0.10,
    "qualification": 0.25,
    "proposal": 0.50,
    "negotiation": 0.70,
    "commit": 0.85,
    "closed_won": 1.00,
    "closed_lost": 0.00,
}


def _to_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def analyze_pipeline(opportunities: List[Dict[str, Any]], stage_probabilities: Dict[str, float] | None = None) -> Dict[str, Any]:
    probs = dict(DEFAULT_STAGE_PROBABILITIES)
    probs.update({k.lower(): float(v) for k, v in (stage_probabilities or {}).items()})

    total_pipeline = 0.0
    weighted_pipeline = 0.0
    stage_counts: Dict[str, int] = {}
    stage_values: Dict[str, float] = {}
    stale_deals: List[Dict[str, Any]] = []

    now = datetime.now(timezone.utc)

    for opp in opportunities:
        stage = str(opp.get("stage", "prospecting")).lower()
        value = float(opp.get("value", 0) or 0)
        probability = probs.get(stage, 0.0)

        total_pipeline += value
        weighted_pipeline += value * probability

        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        stage_values[stage] = stage_values.get(stage, 0.0) + value

        updated_at = _to_date(opp.get("last_updated"))
        if updated_at is not None and (now - updated_at).days >= 30 and stage not in {"closed_won", "closed_lost"}:
            stale_deals.append(
                {
                    "opportunity_name": opp.get("opportunity_name", "unknown"),
                    "stage": stage,
                    "days_stale": (now - updated_at).days,
                    "owner": opp.get("owner", "unassigned"),
                }
            )

    total_open = sum(c for s, c in stage_counts.items() if s not in {"closed_won", "closed_lost"})
    conversion_rates = {}
    for stage in ["prospecting", "qualification", "proposal", "negotiation", "commit"]:
        current = stage_counts.get(stage, 0)
        if current == 0:
            conversion_rates[stage] = None
            continue
        # simple progression estimate based on next stage count / current stage count
        order = ["prospecting", "qualification", "proposal", "negotiation", "commit", "closed_won"]
        idx = order.index(stage)
        next_stage = order[idx + 1]
        conversion_rates[stage] = round((stage_counts.get(next_stage, 0) / current) * 100, 2)

    coverage_ratio = None
    close_target = sum(float(o.get("close_target", 0) or 0) for o in opportunities)
    if close_target > 0:
        coverage_ratio = round(weighted_pipeline / close_target, 2)

    bottlenecks = [
        {"stage": stage, "count": count, "reason": "High volume with low progression"}
        for stage, count in sorted(stage_counts.items(), key=lambda item: item[1], reverse=True)
        if stage not in {"closed_won", "closed_lost"} and count >= 3 and (conversion_rates.get(stage) is None or conversion_rates.get(stage, 0) < 30)
    ]

    recommendations = []
    if stale_deals:
        recommendations.append("Run stale-deal cleanup and requalification for deals inactive > 30 days.")
    if bottlenecks:
        recommendations.append("Focus enablement on bottleneck stages and tighten exit criteria.")
    if weighted_pipeline < total_pipeline * 0.45:
        recommendations.append("Increase late-stage deal quality to improve weighted pipeline conversion confidence.")

    return {
        "module": "pipeline_analysis",
        "total_pipeline": round(total_pipeline, 2),
        "weighted_pipeline": round(weighted_pipeline, 2),
        "pipeline_coverage": coverage_ratio,
        "open_opportunities": total_open,
        "stage_counts": stage_counts,
        "stage_values": {k: round(v, 2) for k, v in stage_values.items()},
        "conversion_rates": conversion_rates,
        "velocity": {"stale_deals_over_30_days": len(stale_deals)},
        "bottlenecks": bottlenecks,
        "stale_deals": stale_deals,
        "recommendations": recommendations,
    }
