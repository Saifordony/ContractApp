from datetime import datetime, timezone
from backend.services.analysis_service import CLAUSE_PATTERNS

BENCHMARK_EXPECTATIONS = {
    "termination": "Clear termination rights, notice periods, cure periods, and survival obligations.",
    "payment": "Specific payment amounts, timing, invoicing process, late-payment handling, and dispute process.",
    "confidentiality": "Clear confidential information definition, exclusions, permitted disclosure, duration, and return/destruction duties.",
    "intellectual_property": "Explicit ownership, licenses, pre-existing IP carve-outs, and work product treatment.",
    "dispute_resolution": "Escalation path, forum, procedure, governing venue, and interim relief rights.",
    "liability": "Balanced liability cap, excluded damages, indemnity scope, and important exceptions.",
    "renewal": "Renewal term, notice window, pricing changes, and opt-out process.",
    "governing_law": "Clear governing law and venue aligned with the parties' operating needs.",
}


def _status_for(found: bool, clause_type: str) -> str:
    if not found:
        return "Missing"
    if clause_type in {"termination", "payment", "confidentiality", "liability", "governing_law"}:
        return "Moderate alignment"
    return "Strong alignment"


def benchmark_analysis(analysis: dict):
    clauses = analysis.get("clauses", []) if analysis else []
    found = {c.get("type"): bool(c.get("found") or c.get("status") == "found") for c in clauses}
    comparisons = []
    aligned = partial = missing = 0
    for key in CLAUSE_PATTERNS:
        status = _status_for(bool(found.get(key)), key)
        if status == "Strong alignment":
            aligned += 1
        elif status == "Moderate alignment":
            partial += 1
        else:
            missing += 1
        label = key.replace("_", " ").title()
        comparisons.append({
            "clause": label,
            "your_contract_status": status,
            "benchmark_expectation": BENCHMARK_EXPECTATIONS.get(key, "Clear, specific, balanced drafting."),
            "gap_assessment": "The clause is present but should be reviewed for completeness against the illustrative profile." if found.get(key) else "The clause was not detected, so this is a clear gap against the illustrative benchmark profile.",
            "plain_english_explanation": f"This comparison checks whether the contract has a practical {label} structure and enough detail for a reviewer to rely on.",
            "improvement_suggestion": f"Strengthen the {label} clause with clear scope, process, timing, responsibilities, and exceptions." if found.get(key) else f"Add a {label} clause if it is relevant to the transaction.",
        })
    total = max(1, len(comparisons))
    score = int(((aligned * 1.0) + (partial * 0.6)) / total * 100)
    return {
        "benchmark_mode": "Illustrative benchmark comparison",
        "benchmark_profiles": ["Baseline Employment Contract Template", "Strong Employer-Protective Template", "Balanced Market Practice Template", "Employee-Friendly Template"],
        "overall_score": score,
        "aligned_clauses": aligned,
        "partially_aligned_clauses": partial,
        "missing_or_weak_clauses": missing,
        "market_position": "Strong alignment" if score >= 80 else "Moderate alignment" if score >= 55 else "Needs strengthening",
        "narrative_summary": "This comparison uses internal illustrative benchmark profiles, not live market data. It highlights where the selected contract appears aligned, partial, or missing against common contract structures.",
        "clause_alignment": comparisons,
        "missing_protections": [item["clause"] for item in comparisons if item["your_contract_status"] == "Missing"],
        "recommended_improvements": [{"action": item["improvement_suggestion"], "rationale": item["gap_assessment"], "related_clause": item["clause"], "priority": "High" if item["your_contract_status"] == "Missing" else "Medium", "source": "illustrative benchmark comparison"} for item in comparisons if item["your_contract_status"] != "Strong alignment"],
        "evidence_or_rule_basis": "Synthetic illustrative profiles based on common contract structure expectations; not external market data.",
        "degraded_mode": False,
    }


async def benchmark_contract(db, owner_user_id: str, contract: dict, analysis: dict | None):
    result = benchmark_analysis(analysis or contract.get("analysis_summary") or {})
    await db.benchmarks.insert_one({"owner_user_id": owner_user_id, "contract_id": str(contract["_id"]), "result": result, "created_at": datetime.now(timezone.utc)})
    return result
