"""Rule-based contract health helpers."""

from typing import Any, Dict


CRITICAL_CLAUSES = {
    "Payment Terms Clause",
    "Confidentiality Clause",
    "Termination Clause",
    "Dispute Resolution Clause",
    "Governing Law / Choice of Law Clause",
}


def evaluate_contract_health_from_clauses(
    clauses: Dict[str, str], response_language: str = "english"
) -> Dict[str, Any]:
    if not isinstance(clauses, dict):
        clauses = {}

    existing = set(clauses.keys())
    missing = sorted(CRITICAL_CLAUSES - existing)
    health_score = max(0, 100 - (len(missing) * 15))

    risk_level = "low" if health_score >= 80 else "medium" if health_score >= 50 else "high"
    approved = health_score >= 70

    required_changes = [f"Add or strengthen: {name}" for name in missing]

    return {
        "approved": approved,
        "health_score": health_score,
        "risk_level": risk_level,
        "missing_critical_clauses": missing,
        "required_changes": required_changes,
        "issues": required_changes,
        "contract_type": "general",
        "response_language": response_language,
    }
