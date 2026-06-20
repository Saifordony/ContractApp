from datetime import datetime, timezone
from backend.services.analysis_service import CLAUSE_PATTERNS


def benchmark_analysis(analysis: dict):
    clauses = analysis.get("clauses", []) if analysis else []
    found = {c["type"]: c.get("found", False) for c in clauses}
    clause_alignment = [{"clause": key.replace("_", " ").title(), "aligned": bool(found.get(key)), "basis": "Found in contract text" if found.get(key) else "Not found by rule-based review"} for key in CLAUSE_PATTERNS]
    missing = [item["clause"] for item in clause_alignment if not item["aligned"]]
    score = int(sum(1 for i in clause_alignment if i["aligned"]) / len(clause_alignment) * 100) if clause_alignment else 0
    return {"overall_score": score, "clause_alignment": clause_alignment, "missing_protections": missing, "market_position": "Strong" if score >= 80 else "Developing" if score >= 55 else "Weak", "recommended_improvements": [f"Add or strengthen {m}." for m in missing[:6]], "evidence_or_rule_basis": "Rule-based comparison against a practical standard contract structure.", "degraded_mode": False}

async def benchmark_contract(db, owner_user_id: str, contract: dict, analysis: dict | None):
    result = benchmark_analysis(analysis or contract.get("analysis_summary") or {})
    await db.benchmarks.insert_one({"owner_user_id": owner_user_id, "contract_id": str(contract["_id"]), "result": result, "created_at": datetime.now(timezone.utc)})
    return result
