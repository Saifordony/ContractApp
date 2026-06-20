"""Canonical contract analysis service used by compatibility and primary routes.

Routers should validate HTTP inputs, then delegate here. This module owns the
single analysis shape for clause extraction, grounded analysis, and deterministic
health scoring. Legacy endpoints may adapt the returned payload, but should not
reimplement analysis business logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from backend.gen1 import evaluate_contract, explain_clauses_for_layman, extract_text_from_upload_bytes
from backend.llm_config import llm_health_check
from backend.services.contract_health import evaluate_contract_health_from_clauses
from backend.services.contract_intelligence import extract_key_clauses
from backend.services.grounded_analysis import make_llm_callable, run_grounded_analysis

CANONICAL_SCHEMA_VERSION = "contract-analysis.v2"


def found_clause_texts(structured_clauses: Dict[str, Any]) -> Dict[str, str]:
    return {
        key: value.get("extracted_text")
        for key, value in (structured_clauses.get("clauses") or {}).items()
        if isinstance(value, dict) and value.get("status") == "found" and value.get("extracted_text")
    }


def normalize_analysis_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy saved analysis payloads to the canonical v2 shape."""
    if not isinstance(results, dict):
        return {}
    if results.get("schema_version") == CANONICAL_SCHEMA_VERSION:
        return results

    structured = results.get("structured_clauses") or {}
    clauses = results.get("clauses") or found_clause_texts(structured)
    health = results.get("health_evaluation") or {}
    grounded = results.get("grounded_analysis") or {}
    return {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "contract_type": results.get("contract_type") or health.get("contract_type"),
        "structured_clauses": structured,
        "clauses": clauses,
        "health_evaluation": health,
        "grounded_analysis": grounded,
        "analysis_source": results.get("analysis_source") or "legacy_normalized",
        "created_at": results.get("created_at"),
        "final_report_summary": results.get("final_report_summary") or {
            "approved": health.get("approved"),
            "health_score": health.get("health_score"),
            "risk_level": health.get("risk_level"),
            "missing_critical_clauses": health.get("missing_critical_clauses", []),
            "required_changes": health.get("required_changes", []),
        },
    }


async def build_health_evaluation(
    clauses: Dict[str, Any],
    *,
    response_language: str = "english",
    contract_text: str = "",
) -> Dict[str, Any]:
    """Canonical health evaluator: deterministic score first, LLM narrative second."""
    health_input = clauses or ({"summary": contract_text[:500]} if contract_text else {})
    rule_evaluation = evaluate_contract_health_from_clauses(health_input, response_language=response_language)
    llm_health = llm_health_check()
    llm_evaluation: Dict[str, Any] = {
        "degraded_mode": True,
        "reasoning": "LLM narrative unavailable; deterministic rule scoring was used.",
    }
    if llm_health.get("reachable"):
        try:
            llm_evaluation = await evaluate_contract(health_input, response_language=response_language)
        except Exception as exc:  # keep deterministic score available
            llm_evaluation = {"degraded_mode": True, "error": exc.__class__.__name__}

    llm_degraded = bool(llm_evaluation.get("degraded_mode")) or not llm_health.get("reachable")
    return {
        "health_score": rule_evaluation.get("health_score"),
        "approved": rule_evaluation.get("approved"),
        "risk_level": rule_evaluation.get("risk_level", "medium"),
        "contract_type": rule_evaluation.get("contract_type"),
        "jurisdiction": rule_evaluation.get("jurisdiction"),
        "missing_critical_clauses": rule_evaluation.get("missing_critical_clauses", []),
        "required_changes": rule_evaluation.get("required_changes", []),
        "dimensions": rule_evaluation.get("dimensions", {}),
        "reasoning": (rule_evaluation if llm_degraded else llm_evaluation).get("reasoning"),
        "scoring_source": "rule_engine",
        "narrative_source": "rule_based_fallback" if llm_degraded else "llm",
        "llm_assessment": llm_evaluation,
        "degraded_mode": llm_degraded,
        "module": "contract_health",
    }


async def analyze_contract_text(
    contract_text: str,
    *,
    response_language: str = "english",
    include_clause_explanations: bool = True,
    debug: bool = False,
) -> Dict[str, Any]:
    text = (contract_text or "").strip()
    if len(text) < 100:
        raise ValueError("Contract text is too short to analyze.")

    structured_clauses = extract_key_clauses(text)
    clauses = found_clause_texts(structured_clauses)
    clause_explanations = (
        await explain_clauses_for_layman(clauses, response_language=response_language)
        if include_clause_explanations and clauses
        else {}
    )
    grounded = run_grounded_analysis(text, llm_callable=make_llm_callable(), debug=debug)
    health = await build_health_evaluation(clauses, response_language=response_language, contract_text=text)

    canonical = {
        "schema_version": CANONICAL_SCHEMA_VERSION,
        "contract_type": health.get("contract_type"),
        "structured_clauses": structured_clauses,
        "clauses": clauses,
        "clause_explanations": clause_explanations,
        "health_evaluation": health,
        "grounded_analysis": grounded,
        "analysis_source": "contract_analysis_service",
        "created_at": datetime.utcnow(),
        "final_report_summary": {
            "approved": health.get("approved"),
            "health_score": health.get("health_score"),
            "risk_level": health.get("risk_level"),
            "missing_critical_clauses": health.get("missing_critical_clauses", []),
            "required_changes": health.get("required_changes", []),
        },
    }
    return canonical


async def analyze_uploaded_contract(
    file_bytes: bytes,
    filename: str,
    *,
    content_type: Optional[str] = None,
    use_ocr: bool = True,
    response_language: str = "english",
) -> Dict[str, Any]:
    extracted = extract_text_from_upload_bytes(
        file_bytes,
        filename,
        content_type=content_type,
        use_ocr=use_ocr,
        response_language=response_language,
    )
    analysis = await analyze_contract_text(
        extracted.get("text", ""),
        response_language=response_language,
        include_clause_explanations=True,
    )
    analysis["contract_text"] = extracted.get("text", "")
    analysis["used_ocr"] = bool(extracted.get("used_ocr"))
    analysis["ocr_confidence"] = extracted.get("ocr_confidence")
    return analysis


def to_grounded_response(canonical: Dict[str, Any]) -> Dict[str, Any]:
    return canonical.get("grounded_analysis", {})


def to_legacy_clause_response(canonical: Dict[str, Any]) -> Dict[str, Any]:
    response = {
        "structured_clauses": canonical.get("structured_clauses", {}),
        "clause_explanations": canonical.get("clause_explanations", {}),
    }
    for key in ("contract_text", "used_ocr", "ocr_confidence"):
        if key in canonical:
            response[key] = canonical[key]
    if canonical.get("used_ocr") and canonical.get("ocr_confidence") is not None and canonical.get("ocr_confidence", 1) < 0.45:
        response["ocr_warning"] = "The scan quality is low, so some extracted text may be inaccurate."
    return response
