from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

BenchmarkCommentaryFn = Callable[[Dict[str, Any]], str]

WEIGHT_POINTS = {"High": 3, "Medium": 2, "Low": 1}

BASELINES: Dict[str, List[Dict[str, Any]]] = {
    "employment": [
        {"review_area": "Parties", "clause_keys": ["parties"], "benchmark_expectation": "The contract should clearly identify employer and employee names, roles, and identifying details.", "expected_evidence": ["employer", "employee", "between"], "severity_if_missing": "High", "scoring_weight": "High", "typical_term_expectation": None, "user_friendly_explanation": "Users should know exactly who is bound by the agreement."},
        {"review_area": "Role / Position", "clause_keys": ["scope_of_work"], "benchmark_expectation": "Employment contracts should clearly state role, title, responsibilities, and reporting or work expectations.", "expected_evidence": ["role", "position", "responsibilities", "duties"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "The employee should understand what work is expected."},
        {"review_area": "Start Date", "clause_keys": ["effective_date"], "benchmark_expectation": "The start date or effective date should be clearly stated.", "expected_evidence": ["effective", "start", "commencement"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "A clear start date avoids uncertainty."},
        {"review_area": "Compensation", "clause_keys": ["compensation", "payment_terms"], "benchmark_expectation": "Salary, currency, payment frequency, benefits, allowances, deductions, and salary review terms should be clearly stated.", "expected_evidence": ["salary", "currency", "monthly", "benefits", "allowances", "deductions"], "severity_if_missing": "Critical", "scoring_weight": "High", "typical_term_expectation": "Payment frequency should be clear.", "user_friendly_explanation": "Pay terms are one of the most important employment terms."},
        {"review_area": "Benefits", "clause_keys": ["compensation", "miscellaneous"], "benchmark_expectation": "Benefits, allowances, insurance, deductions, and other employment benefits should be clear where applicable.", "expected_evidence": ["benefits", "allowance", "insurance", "deduction"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Benefits can materially affect the employee's total package."},
        {"review_area": "Working Hours", "clause_keys": ["working_hours"], "benchmark_expectation": "Weekly hours, working days, overtime, and work arrangement should be stated.", "expected_evidence": ["hours", "weekly", "overtime", "working days"], "severity_if_missing": "High", "scoring_weight": "High", "typical_term_expectation": "Weekly hours and overtime policy should be clear.", "user_friendly_explanation": "Working time and overtime expectations should not be ambiguous."},
        {"review_area": "Probation", "clause_keys": ["probation"], "benchmark_expectation": "Probation duration and conditions should be stated.", "expected_evidence": ["probation", "trial"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": "3 to 6 months where legally applicable.", "user_friendly_explanation": "Probation rules explain early-employment rights and exit conditions."},
        {"review_area": "Leave Policy", "clause_keys": ["leave_policy"], "benchmark_expectation": "Annual leave, sick leave, public holidays, and leave approval process should be stated.", "expected_evidence": ["annual leave", "sick leave", "holiday", "approval"], "severity_if_missing": "High", "scoring_weight": "High", "typical_term_expectation": "Annual leave, sick leave, and public holidays should be addressed.", "user_friendly_explanation": "Leave entitlement is a core employment protection."},
        {"review_area": "Confidentiality", "clause_keys": ["confidentiality"], "benchmark_expectation": "Confidentiality duties, protected information, and duration should be clearly defined.", "expected_evidence": ["confidential", "non-disclosure", "duration"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Confidentiality controls how business information is protected."},
        {"review_area": "IP Assignment", "clause_keys": ["intellectual_property"], "benchmark_expectation": "Ownership of work product and intellectual property created during employment should be stated.", "expected_evidence": ["intellectual property", "ownership", "work product"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "IP wording avoids disputes over work created during employment."},
        {"review_area": "Termination", "clause_keys": ["termination"], "benchmark_expectation": "Notice period, termination grounds, termination process, and final settlement/end-of-service reference should be stated.", "expected_evidence": ["notice", "terminate", "grounds", "settlement"], "severity_if_missing": "Critical", "scoring_weight": "High", "typical_term_expectation": "Clear notice period should be stated.", "user_friendly_explanation": "Termination language is critical because it controls how the relationship ends."},
        {"review_area": "Governing Law", "clause_keys": ["governing_law"], "benchmark_expectation": "Applicable law, jurisdiction, or courts should be stated.", "expected_evidence": ["governed", "law", "jurisdiction", "courts"], "severity_if_missing": "High", "scoring_weight": "High", "typical_term_expectation": None, "user_friendly_explanation": "Governing law tells users which legal system applies."},
        {"review_area": "Dispute Resolution", "clause_keys": ["dispute_resolution"], "benchmark_expectation": "The contract should define whether disputes go to court, arbitration, mediation, or another mechanism.", "expected_evidence": ["dispute", "court", "arbitration", "mediation"], "severity_if_missing": "High", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Dispute wording explains how disagreements are handled."},
        {"review_area": "Non-Compete / Non-Solicit", "clause_keys": ["non_compete"], "benchmark_expectation": "If restrictions apply after employment, duration, scope, geography, and reasonableness should be clear.", "expected_evidence": ["non-compete", "competitor", "non-solicit"], "severity_if_missing": "Low", "scoring_weight": "Low", "typical_term_expectation": "Any restriction should be reasonable and specific.", "user_friendly_explanation": "Post-employment restrictions should be narrow and understandable."},
    ],
    "service_agreement": [
        {"review_area": "Parties", "clause_keys": ["parties"], "benchmark_expectation": "The agreement should identify all contracting parties and their roles.", "expected_evidence": ["between", "client", "provider"], "severity_if_missing": "High", "scoring_weight": "High", "typical_term_expectation": None, "user_friendly_explanation": "Parties must be clear."},
        {"review_area": "Scope of Work", "clause_keys": ["scope_of_work"], "benchmark_expectation": "Services, deliverables, exclusions, and responsibilities should be clearly described.", "expected_evidence": ["services", "deliverables", "scope"], "severity_if_missing": "Critical", "scoring_weight": "High", "typical_term_expectation": None, "user_friendly_explanation": "Scope controls what must be delivered."},
        {"review_area": "Fees / Payment Terms", "clause_keys": ["payment_terms", "compensation"], "benchmark_expectation": "Fees, invoicing, due dates, taxes, and late payment consequences should be stated.", "expected_evidence": ["invoice", "fees", "payment", "due"], "severity_if_missing": "Critical", "scoring_weight": "High", "typical_term_expectation": "Payment timing should be clear.", "user_friendly_explanation": "Payment clarity prevents disputes."},
        {"review_area": "Change Control", "clause_keys": ["miscellaneous"], "benchmark_expectation": "Changes should require written approval or change orders.", "expected_evidence": ["change order", "amendment", "written approval"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Change control prevents scope creep."},
        {"review_area": "Confidentiality", "clause_keys": ["confidentiality"], "benchmark_expectation": "Confidentiality obligations should be stated.", "expected_evidence": ["confidential"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Confidentiality protects business information."},
        {"review_area": "IP Ownership", "clause_keys": ["intellectual_property"], "benchmark_expectation": "Ownership or license rights in deliverables should be clear.", "expected_evidence": ["intellectual property", "ownership", "license"], "severity_if_missing": "High", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "IP terms clarify who owns deliverables."},
        {"review_area": "Liability", "clause_keys": ["limitation_of_liability"], "benchmark_expectation": "Liability caps and excluded damages should be addressed.", "expected_evidence": ["liability", "damages", "cap"], "severity_if_missing": "High", "scoring_weight": "High", "typical_term_expectation": None, "user_friendly_explanation": "Liability clauses allocate financial risk."},
        {"review_area": "Indemnity", "clause_keys": ["indemnification"], "benchmark_expectation": "Third-party claim responsibilities should be addressed.", "expected_evidence": ["indemnify", "claim"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Indemnity explains who pays for certain claims."},
        {"review_area": "Termination", "clause_keys": ["termination"], "benchmark_expectation": "Termination rights, notice, and transition obligations should be stated.", "expected_evidence": ["terminate", "notice"], "severity_if_missing": "High", "scoring_weight": "High", "typical_term_expectation": "Clear notice period should be stated.", "user_friendly_explanation": "Exit terms should be clear."},
        {"review_area": "Governing Law", "clause_keys": ["governing_law"], "benchmark_expectation": "Applicable law should be stated.", "expected_evidence": ["law", "governed"], "severity_if_missing": "High", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Governing law gives legal certainty."},
        {"review_area": "Dispute Resolution", "clause_keys": ["dispute_resolution"], "benchmark_expectation": "Dispute forum and process should be stated.", "expected_evidence": ["dispute", "court", "arbitration"], "severity_if_missing": "High", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Dispute process reduces uncertainty."},
    ],
}

BASELINES["general"] = BASELINES["service_agreement"]
BASELINES["nda"] = [
    {"review_area": "Parties", "clause_keys": ["parties"], "benchmark_expectation": "The NDA should identify disclosing and receiving parties.", "expected_evidence": ["between", "party"], "severity_if_missing": "High", "scoring_weight": "High", "typical_term_expectation": None, "user_friendly_explanation": "Parties must be clear."},
    {"review_area": "Definition of Confidential Information", "clause_keys": ["confidentiality"], "benchmark_expectation": "Confidential information should be defined clearly.", "expected_evidence": ["confidential information", "includes"], "severity_if_missing": "Critical", "scoring_weight": "High", "typical_term_expectation": None, "user_friendly_explanation": "The NDA must define what is protected."},
    {"review_area": "Confidentiality Obligations", "clause_keys": ["confidentiality"], "benchmark_expectation": "Use and disclosure obligations should be clear.", "expected_evidence": ["shall not disclose", "use"], "severity_if_missing": "Critical", "scoring_weight": "High", "typical_term_expectation": None, "user_friendly_explanation": "Obligations explain what the receiving party must do."},
    {"review_area": "Duration", "clause_keys": ["termination", "miscellaneous"], "benchmark_expectation": "The confidentiality duration or survival period should be stated.", "expected_evidence": ["duration", "survive", "years"], "severity_if_missing": "Medium", "scoring_weight": "Medium", "typical_term_expectation": "Duration should be clear.", "user_friendly_explanation": "Duration tells users how long secrecy obligations last."},
    {"review_area": "Governing Law", "clause_keys": ["governing_law"], "benchmark_expectation": "Applicable law should be stated.", "expected_evidence": ["law", "governed"], "severity_if_missing": "High", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Governing law gives legal certainty."},
    {"review_area": "Dispute Resolution", "clause_keys": ["dispute_resolution"], "benchmark_expectation": "Dispute forum and process should be stated.", "expected_evidence": ["dispute", "court", "arbitration"], "severity_if_missing": "High", "scoring_weight": "Medium", "typical_term_expectation": None, "user_friendly_explanation": "Dispute process reduces uncertainty."},
]


def normalize_contract_type(contract_type: Optional[str]) -> str:
    raw = (contract_type or "").strip().lower()
    if "employment" in raw or "employee" in raw:
        return "employment"
    if raw in {"msa", "service", "services", "service_agreement", "vendor"} or "service" in raw:
        return "service_agreement"
    if "nda" in raw or "non" in raw and "disclosure" in raw:
        return "nda"
    return "general"


def display_contract_type(normalized: str) -> str:
    return {
        "employment": "Employment Contract",
        "service_agreement": "Service Agreement",
        "nda": "NDA",
        "general": "General Contract",
    }.get(normalized, "General Contract")


def _clause_text(validated_clauses: Dict[str, Any], keys: List[str]) -> tuple[str, List[Dict[str, str]]]:
    for key in keys:
        payload = validated_clauses.get(key)
        if isinstance(payload, dict) and payload.get("status") == "found" and payload.get("extracted_text"):
            evidence = []
            for item in (payload.get("evidence_snippets") or [])[:2]:
                if isinstance(item, dict) and item.get("quote"):
                    evidence.append({"quote": str(item.get("quote", "")), "location": str(item.get("location", "")), "reason": f"Evidence for {key.replace('_', ' ')}"})
            if not evidence:
                evidence.append({"quote": str(payload.get("extracted_text", ""))[:500], "location": "Validated extracted clause", "reason": f"Evidence for {key.replace('_', ' ')}"})
            return str(payload.get("extracted_text", "")).strip(), evidence
    return "", []


def _quality_score(text: str, expected_evidence: List[str]) -> int:
    if not text:
        return 0
    lower = text.lower()
    matches = sum(1 for token in expected_evidence if token.lower() in lower)
    length_bonus = 1 if len(text) > 160 else 0
    ratio = min(1.0, (matches + length_bonus) / max(len(expected_evidence), 1))
    return int(round(ratio * 100))


def _result_label(text: str, quality: int) -> str:
    if not text:
        return "Not found"
    if quality >= 70:
        return "Aligned"
    if quality >= 35:
        return "Partially aligned"
    return "Below benchmark"


def _position_label(score: int) -> str:
    if score >= 85:
        return "Strongly Aligned"
    if score >= 70:
        return "Mostly Aligned"
    if score >= 50:
        return "Partially Aligned"
    if score >= 30:
        return "Below Expected Standard"
    return "Significantly Below Expected Standard"


def _extract_first(pattern: str, text: str) -> Optional[str]:
    match = re.search(pattern, text or "", flags=re.IGNORECASE)
    return match.group(0).strip() if match else None


def _market_terms(validated_clauses: Dict[str, Any], normalized_type: str) -> List[Dict[str, str]]:
    terms = []
    checks = [
        ("Monthly Salary", ["compensation", "payment_terms"], r"(?:JOD|USD|AED|SAR|QAR|EUR|GBP|\$)\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:JOD|USD|AED|SAR|QAR|EUR|GBP)", "Salary should be stated, but no salary benchmark dataset is available for market comparison."),
        ("Payment Frequency", ["compensation", "payment_terms"], r"\b(?:monthly|weekly|biweekly|quarterly|annually|month end|end of each month)\b", "Payment frequency should be clear."),
        ("Probation Period", ["probation"], r"\b\d+\s?(?:month|months|day|days)\b", "3 to 6 months where legally applicable."),
        ("Notice Period", ["termination"], r"\b\d+\s?(?:day|days|month|months)\b", "Clear notice period should be stated."),
        ("Working Hours Per Week", ["working_hours"], r"\b\d+\s?(?:hours|hrs)\b", "Weekly hours and overtime policy should be clear."),
        ("Annual Leave Days", ["leave_policy"], r"\b\d+\s?(?:days|day)\b", "Annual leave, sick leave, and public holidays should be stated."),
        ("Confidentiality Duration", ["confidentiality"], r"\b\d+\s?(?:years|year|months|month)\b", "Confidentiality duration should be clear if time-limited."),
        ("Non-Compete Duration", ["non_compete"], r"\b\d+\s?(?:years|year|months|month)\b", "Any non-compete duration should be reasonable and specific."),
    ]
    for term, keys, pattern, expectation in checks:
        text, _ = _clause_text(validated_clauses, keys)
        found = _extract_first(pattern, text)
        if found:
            if term == "Monthly Salary":
                difference = "Stated — no market average available"
                interpretation = "Comparison limited"
            elif term == "Probation Period" and re.search(r"\b[3-6]\s?months?\b", found, flags=re.IGNORECASE):
                difference = "Within expected range"
                interpretation = "Aligned"
            else:
                difference = "Stated"
                interpretation = "Aligned"
            your_contract = found
        else:
            your_contract = "Not found — comparison unavailable."
            difference = "N/A"
            interpretation = "Comparison unavailable because the term was not found"
        terms.append({
            "term": term,
            "your_contract": your_contract,
            "benchmark_average": expectation,
            "benchmark_range": expectation if term == "Probation Period" else "Rule-based expectation only; no live market range available.",
            "difference": difference,
            "interpretation": interpretation,
            "limitations": "Rule-based benchmark, not live market data.",
        })
    return terms


def benchmark_sample_size(contract_type: str) -> Optional[int]:
    seed_path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "benchmark_seed.json"
    if not seed_path.exists():
        return None
    try:
        items = json.loads(seed_path.read_text())
    except Exception:
        return None
    normalized = normalize_contract_type(contract_type)
    aliases = {"employment": {"employment"}, "service_agreement": {"msa", "service_agreement", "vendor"}, "nda": {"nda"}, "general": set()}
    valid = aliases.get(normalized, set())
    count = sum(1 for item in items if str(item.get("contract_type", "")).lower() in valid)
    return count or None


def build_benchmark_comparison(
    *,
    contract_id: str,
    validated_clauses: Dict[str, Any],
    raw_contract_text: str = "",
    contract_type: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    readiness_review: Optional[Dict[str, Any]] = None,
    ai_commentary_fn: Optional[BenchmarkCommentaryFn] = None,
) -> Dict[str, Any]:
    normalized_type = normalize_contract_type(contract_type)
    baseline = BASELINES.get(normalized_type)
    if not baseline:
        raise ValueError(f"Missing benchmark baseline for {normalized_type}")

    sample_size = benchmark_sample_size(normalized_type)
    basis = f"Rule-based {display_contract_type(normalized_type).lower()} standard"
    limitations = ["No live market dataset was available. This comparison uses internal rule-based benchmark expectations."]
    if sample_size:
        basis += f" with seeded benchmark corpus references (N={sample_size})"
        limitations.append("Seeded corpus is small and should not be treated as live market data.")

    rows = []
    strengths: List[str] = []
    gaps: List[str] = []
    must_fix: List[str] = []
    recommended: List[str] = []
    total_weight = 0
    coverage_points = quality_points = term_points = evidence_points = 0.0

    for rule in baseline:
        weight = WEIGHT_POINTS.get(rule["scoring_weight"], 1)
        total_weight += weight
        text, evidence = _clause_text(validated_clauses, rule["clause_keys"])
        quality = _quality_score(text, rule["expected_evidence"])
        result = _result_label(text, quality)
        if text:
            coverage_points += weight
            quality_points += weight * (quality / 100)
            evidence_points += weight if evidence else weight * 0.4
            if rule.get("typical_term_expectation"):
                term_points += weight * 0.8
        recommendation = "No immediate benchmark action required."
        if result == "Not found":
            gap = f"{rule['review_area']} is not clearly found. {rule['benchmark_expectation']}"
            gaps.append(gap)
            recommendation = f"Add or clarify {rule['review_area']}: {rule['benchmark_expectation']}"
            if rule["severity_if_missing"] in {"Critical", "High"}:
                must_fix.append(recommendation)
            else:
                recommended.append(recommendation)
        elif result == "Partially aligned" or result == "Below benchmark":
            gap = f"{rule['review_area']} is present but incomplete against benchmark expectations."
            gaps.append(gap)
            recommendation = f"Strengthen {rule['review_area']}: {rule['benchmark_expectation']}"
            recommended.append(recommendation)
        else:
            strengths.append(f"{rule['review_area']} is aligned with the benchmark expectation.")

        rows.append({
            "review_area": rule["review_area"],
            "your_contract": text or "Not found — comparison unavailable.",
            "benchmark_expectation": rule["benchmark_expectation"],
            "result": result,
            "severity": rule["severity_if_missing"] if result == "Not found" else "Medium" if result == "Partially aligned" else "Low",
            "evidence": evidence,
            "recommendation": recommendation,
            "why_this_matters": rule["user_friendly_explanation"],
            "clause_summary": (text[:220] + "...") if len(text or "") > 220 else (text or "Not found — comparison unavailable."),
            "peer_group_size": None,
            "confidence_label": "Medium" if text else "Low",
            "outlier_label": "Outlier" if result in {"Not found", "Below benchmark"} else "Slightly different" if result == "Partially aligned" else "Aligned",
        })

    total_weight = max(total_weight, 1)
    alignment_score = int(round(
        (coverage_points / total_weight) * 50
        + (quality_points / total_weight) * 30
        + (term_points / total_weight) * 15
        + (evidence_points / total_weight) * 5
    ))
    position = _position_label(alignment_score)
    top_reasons = gaps[:3] or strengths[:3]
    executive_summary = (
        f"Benchmark Alignment Score: {alignment_score}/100. Position: {position}. "
        f"This comparison uses {basis}. "
        + ("Key drivers: " + " ".join(top_reasons[:3]) if top_reasons else "No major benchmark gaps were detected from the validated evidence.")
    )

    result = {
        "benchmark_title": "Benchmark Comparison",
        "benchmark_context": {
            "contract_type": display_contract_type(normalized_type),
            "region": "MENA" if normalized_type in {"employment", "service_agreement", "nda", "general"} else "Not clearly detected",
            "jurisdiction": jurisdiction or "Not clearly detected",
            "benchmark_basis": basis,
            "sample_size": sample_size,
            "confidence_label": "Medium" if normalized_type != "general" else "Low",
            "limitations": limitations,
        },
        "overall_position": {
            "alignment_score": max(0, min(100, alignment_score)),
            "position_label": position,
            "executive_summary": executive_summary,
            "top_reasons_for_score": top_reasons[:3],
        },
        "your_contract_vs_benchmark": rows,
        "market_terms_comparison": _market_terms(validated_clauses, normalized_type),
        "strengths": strengths[:8],
        "gaps": gaps[:10],
        "priority_recommendations": {
            "priority_1_must_fix": list(dict.fromkeys(must_fix))[:8],
            "priority_2_recommended": list(dict.fromkeys(recommended))[:8],
        },
        "ai_commentary": "AI commentary unavailable.",
    }

    if ai_commentary_fn:
        try:
            commentary = ai_commentary_fn(result)
            if commentary and commentary.strip():
                result["ai_commentary"] = commentary.strip()
        except Exception:
            result["ai_commentary"] = "AI commentary unavailable. Deterministic benchmark comparison completed successfully."

    return result
