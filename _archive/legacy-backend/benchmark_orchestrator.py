"""Official benchmark service facade.

All benchmark routes should call this module so Streamlit-visible endpoints and
legacy upload analysis share one benchmark contract and degraded-mode semantics.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from backend.services.benchmark_comparison_service import build_benchmark_comparison
from backend.services.benchmark_service import run_benchmark_analysis


def compare_saved_contract(
    *,
    contract_id: str,
    validated_clauses: Dict[str, Any],
    raw_contract_text: str,
    contract_type: Optional[str],
    jurisdiction: Optional[str],
    readiness_review: Dict[str, Any],
    ai_commentary_fn: Optional[Callable[[Dict[str, Any]], str]] = None,
) -> Dict[str, Any]:
    result = build_benchmark_comparison(
        contract_id=contract_id,
        validated_clauses=validated_clauses,
        raw_contract_text=raw_contract_text,
        contract_type=contract_type,
        jurisdiction=jurisdiction,
        readiness_review=readiness_review,
        ai_commentary_fn=ai_commentary_fn,
    )
    result.setdefault("benchmark_schema", "benchmark.v2")
    result.setdefault("degraded_mode", ai_commentary_fn is None)
    result.setdefault("evidence_or_rule_basis", result.get("benchmark_context", {}).get("benchmark_basis"))
    return result


def analyze_uploaded_benchmark(**kwargs: Any) -> Dict[str, Any]:
    result = run_benchmark_analysis(**kwargs)
    result.setdefault("benchmark_schema", "benchmark.v2")
    result.setdefault("degraded_mode", True)
    result.setdefault("evidence_or_rule_basis", "Seeded/rule-based benchmark analysis")
    return result
