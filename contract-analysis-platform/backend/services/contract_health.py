from __future__ import annotations

from typing import Any, Dict, List


def _dimension(name: str, score: int, explanation: str, evidence: List[Dict[str, str]]) -> Dict[str, Any]:
    return {
        "name": name,
        "score": max(0, min(100, score)),
        "explanation": explanation,
        "evidence": evidence,
    }


def evaluate_contract_health_from_clauses(clauses: Dict[str, str]) -> Dict[str, Any]:
    normalized = {str(k).lower(): str(v) for k, v in (clauses or {}).items()}

    def has_any(*keys: str) -> bool:
        return any(key in normalized for key in keys)

    dimensions: List[Dict[str, Any]] = []
    red_flags: List[Dict[str, Any]] = []

    risk_score = 80
    risk_evidence: List[Dict[str, str]] = []
    liability_text = normalized.get("limitation of liability clause", "") + normalized.get("liability", "")
    if "unlimited" in liability_text.lower() or "without limitation" in liability_text.lower():
        risk_score = 30
        red_flags.append({"type": "unlimited_liability", "severity": "high", "evidence": [{"quote": liability_text[:240], "location": "clause:liability"}]})
    elif not liability_text:
        risk_score = 45
        red_flags.append({"type": "missing_liability_limit", "severity": "high", "evidence": []})
    if liability_text:
        risk_evidence.append({"quote": liability_text[:240], "location": "clause:liability"})
    dimensions.append(_dimension("Risk Exposure", risk_score, "Assesses liability/indemnity exposure and cap clarity.", risk_evidence))

    comm_score = 85 if has_any("payment terms clause", "payment terms", "scope of work clause") else 50
    comm_evidence = []
    for key in ["payment terms clause", "payment terms", "scope of work clause", "scope of work"]:
        if key in normalized:
            comm_evidence.append({"quote": normalized[key][:240], "location": f"clause:{key}"})
    dimensions.append(_dimension("Commercial Clarity", comm_score, "Checks payment clarity and deliverable definition.", comm_evidence[:2]))

    comp_score = 82 if has_any("confidentiality clause", "confidentiality", "sla_obligations", "obligations") else 55
    comp_evidence = []
    for key in ["confidentiality clause", "confidentiality", "sla_obligations", "obligations"]:
        if key in normalized:
            comp_evidence.append({"quote": normalized[key][:240], "location": f"clause:{key}"})
    dimensions.append(_dimension("Compliance & Obligations", comp_score, "Assesses obligation tracking and compliance language.", comp_evidence[:2]))

    term_score = 78
    term_text = normalized.get("termination clause", "") + normalized.get("renewal", "")
    if "automatic renewal" in term_text.lower() and "notice" not in term_text.lower():
        term_score = 45
        red_flags.append({"type": "auto_renewal_no_notice", "severity": "medium", "evidence": [{"quote": term_text[:240], "location": "clause:term-renewal"}]})
    if not term_text:
        term_score = 40
        red_flags.append({"type": "missing_termination_terms", "severity": "high", "evidence": []})
    dimensions.append(_dimension("Term & Renewal Risk", term_score, "Evaluates renewal mechanics and termination rights.", [{"quote": term_text[:240], "location": "clause:term-renewal"}] if term_text else []))

    law_score = 80 if has_any("governing law / choice of law clause", "governing law", "dispute resolution clause") else 35
    if law_score < 50:
        red_flags.append({"type": "missing_governing_law_or_dispute", "severity": "high", "evidence": []})
    law_evidence = []
    for key in ["governing law / choice of law clause", "governing law", "dispute resolution clause"]:
        if key in normalized:
            law_evidence.append({"quote": normalized[key][:240], "location": f"clause:{key}"})
    dimensions.append(_dimension("Dispute & Governing Law", law_score, "Assesses legal forum and dispute mechanism complexity.", law_evidence[:2]))

    health_score = round(sum(d["score"] for d in dimensions) / max(len(dimensions), 1))
    risk_level = "low" if health_score >= 75 else "medium" if health_score >= 55 else "high"
    approved = health_score >= 65 and not any(flag["severity"] == "high" for flag in red_flags)

    missing = []
    for required in [
        "governing law",
        "dispute resolution clause",
        "termination clause",
        "payment terms clause",
        "confidentiality clause",
    ]:
        if required not in normalized:
            missing.append(required)

    issues = [flag["type"] for flag in red_flags]
    required_changes = []
    if "missing_governing_law_or_dispute" in issues:
        required_changes.append("Add governing law and dispute resolution clauses with explicit jurisdiction.")
    if "unlimited_liability" in issues or "missing_liability_limit" in issues:
        required_changes.append("Define a clear liability cap and carve-outs for gross negligence/fraud only.")
    if "missing_termination_terms" in issues:
        required_changes.append("Add bilateral termination rights and notice periods.")
    if "auto_renewal_no_notice" in issues:
        required_changes.append("Add explicit opt-out notice window for renewal.")

    evidence = []
    for dim in dimensions:
        evidence.extend(dim["evidence"])

    return {
        "approved": approved,
        "reasoning": f"Health score {health_score}/100 across 5 dimensions; risk level is {risk_level}.",
        "missing_critical_clauses": missing,
        "issues": issues,
        "required_changes": required_changes,
        "risk_level": risk_level,
        "health_score": health_score,
        "dimensions": dimensions,
        "red_flags": red_flags,
        "evidence": evidence[:6],
    }
