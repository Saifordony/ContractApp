"""Official hybrid contract analysis service: rule extraction + grounded AI review."""
import io
import json
from datetime import datetime, timezone
from typing import Any

from backend.config import get_settings
from backend.services.llm_service import generate_structured_json, llm_health

CLAUSE_PATTERNS = {
    "termination": ["termination", "terminate", "expiration"],
    "payment": ["payment", "fees", "invoice", "compensation"],
    "confidentiality": ["confidential", "non-disclosure", "proprietary"],
    "liability": ["liability", "indemn", "damages"],
    "intellectual_property": ["intellectual property", "ip rights", "ownership"],
    "governing_law": ["governing law", "jurisdiction", "laws of"],
    "dispute_resolution": ["dispute", "arbitration", "mediation"],
    "renewal": ["renewal", "auto-renew", "automatic renewal"],
}
CRITICAL = ["termination", "payment", "confidentiality", "liability", "governing_law"]


def extract_text(filename: str, content: bytes) -> str:
    name = filename.lower()
    if name.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        try:
            import fitz
            with fitz.open(stream=content, filetype="pdf") as doc:
                return "\n".join(page.get_text() for page in doc)
        except Exception:
            return ""
    if name.endswith(".docx"):
        try:
            from docx import Document
            document = Document(io.BytesIO(content))
            return "\n".join(p.text for p in document.paragraphs)
        except Exception:
            return ""
    return content.decode("utf-8", errors="ignore")


def _evidence_for(text: str, terms: list[str]) -> list[dict[str, Any]]:
    lower = text.lower()
    out = []
    for term in terms:
        idx = lower.find(term)
        if idx >= 0:
            start, end = max(0, idx - 140), min(len(text), idx + 260)
            out.append({"text": text[start:end].strip(), "keyword": term, "source": "rule-based match"})
            break
    return out


def _rule_based_analysis(text: str) -> dict[str, Any]:
    clauses = []
    for key, terms in CLAUSE_PATTERNS.items():
        evidence = _evidence_for(text, terms)
        clauses.append({
            "type": key,
            "title": key.replace("_", " ").title(),
            "status": "found" if evidence else "missing" if key in CRITICAL else "partial",
            "found": bool(evidence),
            "confidence": "high" if evidence else "low",
            "evidence": evidence,
            "rule_based_summary": "Rule-based match found in extracted text." if evidence else "Rule-based extraction did not find direct evidence for this clause.",
        })
    missing = [c for c in CRITICAL if not next(item for item in clauses if item["type"] == c)["found"]]
    found_count = sum(1 for c in clauses if c["found"])
    score = max(15, min(100, int(found_count / len(CLAUSE_PATTERNS) * 100))) if text else 0
    risks = []
    for miss in missing:
        risks.append({"severity": "high" if miss in ["liability", "termination"] else "medium", "title": f"Missing {miss.replace('_',' ')} clause", "affected_clause": miss, "explanation": "A critical protection was not found in the extracted contract text.", "suggested_mitigation": "Add a clear clause tailored to the transaction before signature."})
    return {"clauses": clauses, "missing_critical_clauses": missing, "health_score": score, "risk_level": "High" if score < 55 else "Medium" if score < 80 else "Low", "risks": risks}


def _fallback_ai_fields(rule_result: dict[str, Any], status: str, parse_failed: bool = False, error: str | None = None) -> dict[str, Any]:
    missing = rule_result["missing_critical_clauses"]
    clauses = []
    for clause in rule_result["clauses"]:
        if clause["found"]:
            insight = "LLM unavailable. Rule-based evidence indicates this clause appears in the extracted text; review the quoted evidence for completeness."
            recommendation = "Generic fallback: have a reviewer confirm the clause is complete, balanced, and aligned with the business deal."
            priority = "Medium"
        else:
            insight = "LLM unavailable. Rule-based extraction did not find enough evidence to confirm this clause."
            recommendation = "Generic fallback: consider adding or strengthening this protection if relevant to the transaction."
            priority = "High" if clause["type"] in CRITICAL else "Medium"
        clauses.append({**clause, "ai_insight": insight, "ai_risk_assessment": "Rule-based fallback only; no AI interpretation was generated.", "ai_recommendation": recommendation, "negotiation_note": "Confirm with counsel or the business owner before relying on this result.", "review_priority": priority})
    return {
        "source": "degraded",
        "llm_used": False,
        "degraded_mode": True,
        "ai_status": status,
        "llm_parse_failed": parse_failed,
        "llm_error": error,
        "executive_summary": "Rule-based fallback: the contract was reviewed for common clause signals, but the LLM was not available to generate a contract-specific executive review.",
        "ai_overall_assessment": "No AI assessment was generated. Use the clause evidence, missing-clause list, and health score as deterministic review signals only.",
        "key_strengths": [c["title"] for c in rule_result["clauses"] if c["found"]][:5],
        "key_risks": [r["title"] for r in rule_result["risks"]],
        "missing_clauses": missing,
        "recommended_actions": [r["suggested_mitigation"] for r in rule_result["risks"]] or ["Complete legal review before signature."],
        "clauses": clauses,
        "raw_llm_response": {},
    }


def _ai_prompt(text: str, rule_result: dict[str, Any]) -> str:
    evidence_payload = json.dumps(rule_result, default=str)[:12000]
    contract_excerpt = text[:16000]
    return f"""
Review the following contract as an AI contract review assistant. Use only the contract text, extracted clauses, evidence snippets, missing clause results, and rule-based health score provided. Do not invent facts. Do not provide final legal advice. Use language like AI review, risk signal, and recommended review point. Return structured JSON only.

Required JSON keys: executive_summary, ai_overall_assessment, key_strengths, key_risks, missing_clauses, recommended_actions, clauses.
Each item in clauses must include: type, ai_insight, ai_risk_assessment, ai_recommendation, negotiation_note, review_priority.
If evidence is weak or missing, say: The contract text provided does not show enough evidence to confirm this point.

RULE_BASED_RESULT:
{evidence_payload}

CONTRACT_TEXT:
{contract_excerpt}
"""


def _merge_ai(rule_result: dict[str, Any], ai_output: dict[str, Any]) -> dict[str, Any]:
    ai_clause_by_type = {str(item.get("type", "")).lower(): item for item in ai_output.get("clauses", []) if isinstance(item, dict)}
    clauses = []
    for clause in rule_result["clauses"]:
        ai_clause = ai_clause_by_type.get(clause["type"], {})
        clauses.append({
            **clause,
            "ai_insight": ai_clause.get("ai_insight") or "The AI review did not return a specific insight for this clause.",
            "ai_risk_assessment": ai_clause.get("ai_risk_assessment") or "The contract text provided does not show enough evidence to confirm this point.",
            "ai_recommendation": ai_clause.get("ai_recommendation") or "Review the quoted evidence and confirm whether this clause is complete for the deal.",
            "negotiation_note": ai_clause.get("negotiation_note") or "Confirm this point during legal/business review.",
            "review_priority": ai_clause.get("review_priority") or ("High" if clause["type"] in rule_result["missing_critical_clauses"] else "Medium"),
        })
    return {"clauses": clauses}


def analyze_text(text: str) -> dict[str, Any]:
    settings = get_settings()
    text = (text or "").strip()
    rule_result = _rule_based_analysis(text)
    health = llm_health()
    llm_debug = {"health": health, "model": settings.ollama_model, "ollama_url": settings.ollama_base_url}
    if not health.get("reachable"):
        ai_fields = _fallback_ai_fields(rule_result, "LLM unavailable", error=health.get("error"))
    else:
        try:
            retry = _ai_prompt(text, rule_result) + "\nReturn valid JSON only. No markdown. No prose outside JSON."
            raw_ai = generate_structured_json(_ai_prompt(text, rule_result), retry_prompt=retry)
            merged = _merge_ai(rule_result, raw_ai)
            ai_fields = {
                "source": "hybrid",
                "llm_used": True,
                "degraded_mode": False,
                "ai_status": "LLM analysis completed",
                "llm_parse_failed": False,
                "llm_error": None,
                "executive_summary": raw_ai.get("executive_summary") or "AI review completed, but no executive summary was returned.",
                "ai_overall_assessment": raw_ai.get("ai_overall_assessment") or "AI review completed, but no overall assessment was returned.",
                "key_strengths": raw_ai.get("key_strengths") or [],
                "key_risks": raw_ai.get("key_risks") or [],
                "missing_clauses": raw_ai.get("missing_clauses") or rule_result["missing_critical_clauses"],
                "recommended_actions": raw_ai.get("recommended_actions") or [],
                "clauses": merged["clauses"],
                "raw_llm_response": raw_ai,
            }
        except Exception as exc:
            llm_debug["parse_or_generation_error"] = str(exc)
            ai_fields = _fallback_ai_fields(rule_result, "LLM response could not be parsed", parse_failed=True, error=str(exc))
    evidence_trace = []
    for clause in ai_fields["clauses"]:
        if clause.get("evidence"):
            for item in clause["evidence"]:
                evidence_trace.append({"clause": clause["title"], "text": item.get("text"), "source": item.get("source", "extracted_text"), "keyword": item.get("keyword"), "confidence": clause.get("confidence")})
        else:
            evidence_trace.append({"clause": clause["title"], "text": "No direct evidence captured for this clause.", "source": "rule-based absence", "keyword": None, "confidence": clause.get("confidence")})
    return {
        "schema_version": "hybrid-analysis-v1",
        "health_score": rule_result["health_score"],
        "risk_level": rule_result["risk_level"],
        "source": ai_fields["source"],
        "llm_used": ai_fields["llm_used"],
        "degraded_mode": ai_fields["degraded_mode"],
        "ai_status": ai_fields["ai_status"],
        "active_model": settings.ollama_model,
        "confidence": "High" if ai_fields["llm_used"] and rule_result["health_score"] >= 70 else "Medium" if ai_fields["llm_used"] else "Low",
        "executive_summary": ai_fields["executive_summary"],
        "ai_overall_assessment": ai_fields["ai_overall_assessment"],
        "key_strengths": ai_fields["key_strengths"],
        "key_risks": ai_fields["key_risks"],
        "missing_clauses": ai_fields["missing_clauses"],
        "missing_critical_clauses": rule_result["missing_critical_clauses"],
        "recommended_actions": ai_fields["recommended_actions"],
        "recommended_improvements": ai_fields["recommended_actions"],
        "risks": rule_result["risks"],
        "clauses": ai_fields["clauses"],
        "evidence_trace": evidence_trace,
        "rule_based_result": rule_result,
        "llm_request_status": llm_debug,
        "raw_llm_response": ai_fields["raw_llm_response"],
        "llm_parse_failed": ai_fields["llm_parse_failed"],
        "llm_error": ai_fields["llm_error"],
        "created_at": datetime.now(timezone.utc),
    }


async def analyze_contract_record(db, contract: dict):
    analysis = analyze_text(contract.get("extracted_text", ""))
    doc = {"owner_user_id": contract["owner_user_id"], "contract_id": str(contract["_id"]), "analysis": analysis, "created_at": datetime.now(timezone.utc)}
    result = await db.analyses.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.contracts.update_one({"_id": contract["_id"]}, {"$set": {"latest_analysis_id": str(result.inserted_id), "analysis_summary": analysis, "updated_at": datetime.now(timezone.utc)}})
    return analysis
