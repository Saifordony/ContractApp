"""Regional benchmark baselines and scoring utilities."""

from __future__ import annotations

from typing import Any
import re

REGIONAL_BASELINES = {
    "employment": {
        "region": "MENA",
        "description": "Average employment contract standards for Jordan, UAE, Saudi Arabia, and Qatar",
        "clauses": {
            "compensation": {"weight": 20, "expected_detail_level": "high", "notes": "Should specify base salary, currency, payment frequency, and annual review clause."},
            "working_hours": {"weight": 10, "expected_detail_level": "medium", "notes": "Should specify weekly hours, overtime policy, and weekend arrangement."},
            "leave_policy": {"weight": 10, "expected_detail_level": "medium", "notes": "Should include annual leave days (minimum 14-21 in MENA), sick leave, and public holidays."},
            "probation": {"weight": 8, "expected_detail_level": "medium", "notes": "Should specify duration (typically 3-6 months) and conditions for termination during probation."},
            "termination": {"weight": 15, "expected_detail_level": "high", "notes": "Should include notice period (30-90 days typical), grounds for termination, and end-of-service benefit reference."},
            "confidentiality": {"weight": 12, "expected_detail_level": "medium", "notes": "Should define scope of confidential information and post-employment obligations."},
            "non_compete": {"weight": 8, "expected_detail_level": "low", "notes": "Increasingly common in MENA tech and professional services. Duration and geography should be reasonable."},
            "governing_law": {"weight": 10, "expected_detail_level": "medium", "notes": "Should reference applicable national labor law."},
            "dispute_resolution": {"weight": 7, "expected_detail_level": "low", "notes": "Should specify whether disputes go to court or mediation."},
        },
    },
    "nda": {"region": "MENA", "description": "Regional NDA standards", "clauses": {"definition_of_confidential_info": {"weight": 18, "expected_detail_level": "high", "notes": "Define confidential information clearly."}, "obligations": {"weight": 16, "expected_detail_level": "high", "notes": "Usage and disclosure obligations."}, "term": {"weight": 10, "expected_detail_level": "medium", "notes": "Duration and survival."}, "exclusions": {"weight": 12, "expected_detail_level": "medium", "notes": "Standard exclusions."}, "return_or_destruction": {"weight": 10, "expected_detail_level": "medium", "notes": "Data return process."}, "remedies": {"weight": 10, "expected_detail_level": "medium", "notes": "Injunctive relief rights."}, "governing_law": {"weight": 10, "expected_detail_level": "medium", "notes": "Jurisdiction and law."}, "dispute_resolution": {"weight": 8, "expected_detail_level": "low", "notes": "Arbitration/courts."}, "non_solicitation": {"weight": 6, "expected_detail_level": "low", "notes": "Optional non-solicitation."}}},
    "service_agreement": {"region": "MENA", "description": "Regional services agreement standards", "clauses": {"scope_of_services": {"weight": 18, "expected_detail_level": "high", "notes": "Detailed deliverables."}, "fees_and_payment": {"weight": 16, "expected_detail_level": "high", "notes": "Fees and payment terms."}, "service_levels": {"weight": 10, "expected_detail_level": "medium", "notes": "Performance criteria."}, "term_and_termination": {"weight": 14, "expected_detail_level": "high", "notes": "Term and termination rights."}, "liability": {"weight": 12, "expected_detail_level": "medium", "notes": "Liability limits."}, "confidentiality": {"weight": 10, "expected_detail_level": "medium", "notes": "Data secrecy requirements."}, "ip_ownership": {"weight": 10, "expected_detail_level": "medium", "notes": "IP ownership and license."}, "governing_law": {"weight": 6, "expected_detail_level": "low", "notes": "Applicable law."}, "dispute_resolution": {"weight": 4, "expected_detail_level": "low", "notes": "Dispute process."}}},
    "lease": {"region": "MENA", "description": "Regional lease standards", "clauses": {"rent": {"weight": 20, "expected_detail_level": "high", "notes": "Rent amount and schedule."}, "term": {"weight": 12, "expected_detail_level": "medium", "notes": "Lease period and renewal."}, "security_deposit": {"weight": 10, "expected_detail_level": "medium", "notes": "Deposit handling."}, "maintenance": {"weight": 12, "expected_detail_level": "medium", "notes": "Repair obligations."}, "utilities": {"weight": 8, "expected_detail_level": "low", "notes": "Utility responsibilities."}, "termination": {"weight": 12, "expected_detail_level": "medium", "notes": "Early termination."}, "use_restrictions": {"weight": 8, "expected_detail_level": "low", "notes": "Permitted use."}, "governing_law": {"weight": 10, "expected_detail_level": "medium", "notes": "Applicable tenancy law."}, "dispute_resolution": {"weight": 8, "expected_detail_level": "low", "notes": "Dispute handling."}}},
    "general_commercial": {"region": "MENA", "description": "General MENA commercial contracting standards", "clauses": {"scope": {"weight": 16, "expected_detail_level": "high", "notes": "Scope and obligations."}, "payment_terms": {"weight": 14, "expected_detail_level": "high", "notes": "Payment and invoicing."}, "term_and_termination": {"weight": 14, "expected_detail_level": "high", "notes": "Duration and exit rights."}, "confidentiality": {"weight": 10, "expected_detail_level": "medium", "notes": "Confidentiality protections."}, "liability": {"weight": 12, "expected_detail_level": "medium", "notes": "Liability limits."}, "indemnity": {"weight": 10, "expected_detail_level": "medium", "notes": "Indemnity obligations."}, "force_majeure": {"weight": 8, "expected_detail_level": "low", "notes": "Force majeure handling."}, "governing_law": {"weight": 8, "expected_detail_level": "low", "notes": "Choice of law."}, "dispute_resolution": {"weight": 8, "expected_detail_level": "low", "notes": "Dispute mechanism."}}},
}

CLAUSE_LABELS = {
    "working_hours": "Working Hours",
    "leave_policy": "Leave Policy",
    "non_compete": "Non-Compete",
    "governing_law": "Governing Law",
    "dispute_resolution": "Dispute Resolution",
    "term_and_termination": "Term & Termination",
}

EMPLOYMENT_BENCHMARK_REFERENCE = {
    "salary_monthly_jod_avg": 3500,
    "working_hours_weekly_avg": 48,
    "annual_leave_days_avg": 21,
    "probation_months_avg": 3,
    "notice_days_avg": 30,
}

def _grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def run_benchmark(extracted_clauses: dict[str, Any], contract_type: str) -> dict[str, Any]:
    """Run clause coverage benchmark against regional baselines."""
    normalized_type = contract_type if contract_type in REGIONAL_BASELINES else "general_commercial"
    baseline = REGIONAL_BASELINES[normalized_type]
    clause_breakdown: list[dict[str, Any]] = []
    strengths: list[str] = []
    gaps: list[str] = []
    recommendations: list[str] = []
    score = 0.0
    clauses = extracted_clauses or {}

    for clause, meta in baseline["clauses"].items():
        text = str(clauses.get(clause, "")).strip()
        weight = meta["weight"]
        if len(text) > 80:
            earned = float(weight)
            status = "present"
            note = "Well-detailed. Meets MENA standards."
            strengths.append(clause)
        elif 20 <= len(text) <= 80:
            earned = float(weight) * 0.5
            status = "partial"
            note = "Clause exists but lacks detail for regional expectations."
            recommendations.append(f"Enhance {clause} with clearer, jurisdiction-ready details.")
        else:
            earned = 0.0
            status = "missing"
            note = f"No {clause} clause found. {meta['notes']}"
            gaps.append(clause)
            recommendations.append(f"Add {clause} clause. {meta['notes']}")
        score += earned
        clause_breakdown.append(
            {
                "clause": clause,
                "clause_label": CLAUSE_LABELS.get(clause, clause.replace("_", " ").title()),
                "weight": weight,
                "earned": round(earned, 2),
                "status": status,
                "note": note,
            }
        )

    rounded = int(round(score))
    comparisons: list[dict[str, Any]] = []
    if normalized_type == "employment":
        joined = " ".join(str(v) for v in clauses.values())
        amounts = [int(x) for x in re.findall(r"\b(\d{3,6})\b", joined)]
        salary = next((a for a in amounts if 1000 <= a <= 20000), None)
        if salary:
            comparisons.append(
                {
                    "metric": "Base Salary (monthly)",
                    "contract_value": f"{salary} JOD",
                    "benchmark_value": f"{EMPLOYMENT_BENCHMARK_REFERENCE['salary_monthly_jod_avg']} JOD",
                    "insight": "Above regional average" if salary >= EMPLOYMENT_BENCHMARK_REFERENCE["salary_monthly_jod_avg"] else "Below regional average",
                }
            )
    return {"contract_type": normalized_type, "region": baseline["region"], "score": rounded, "grade": _grade(rounded), "summary": "This contract meets most regional expectations but is missing key clauses typical for MENA agreements." if rounded >= 55 else "This contract is below common regional standards and needs substantial clause improvements.", "clause_breakdown": clause_breakdown, "strengths": strengths[:5], "gaps": gaps[:5], "recommendations": recommendations[:5], "benchmark_comparisons": comparisons}
