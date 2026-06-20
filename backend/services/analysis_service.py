"""Official contract analysis service for uploads, analysis, and compatibility wrappers."""
import io, re
from datetime import datetime, timezone
from typing import Any

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
            out.append({"text": text[start:end].strip(), "keyword": term})
            break
    return out

def analyze_text(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    clauses = []
    for key, terms in CLAUSE_PATTERNS.items():
        evidence = _evidence_for(text, terms)
        clauses.append({"type": key, "title": key.replace("_", " ").title(), "found": bool(evidence), "evidence": evidence})
    missing = [c for c in CRITICAL if not next(item for item in clauses if item["type"] == c)["found"]]
    found_count = sum(1 for c in clauses if c["found"])
    score = max(15, min(100, int(found_count / len(CLAUSE_PATTERNS) * 100))) if text else 0
    risks = []
    for miss in missing:
        risks.append({"severity": "high" if miss in ["liability", "termination"] else "medium", "title": f"Missing {miss.replace('_',' ')} clause", "explanation": "A critical protection was not found in the extracted contract text.", "suggested_mitigation": "Add a clear, negotiated clause before signature."})
    return {"schema_version": "clean-analysis-v1", "source": "rule_based", "degraded_mode": False, "executive_summary": (text[:420] + "...") if len(text) > 420 else text or "No readable text was extracted.", "clauses": clauses, "missing_critical_clauses": missing, "health_score": score, "risk_level": "High" if score < 55 else "Medium" if score < 80 else "Low", "risks": risks, "recommended_improvements": [r["suggested_mitigation"] for r in risks], "created_at": datetime.now(timezone.utc)}

async def analyze_contract_record(db, contract: dict):
    analysis = analyze_text(contract.get("extracted_text", ""))
    doc = {"owner_user_id": contract["owner_user_id"], "contract_id": str(contract["_id"]), "analysis": analysis, "created_at": datetime.now(timezone.utc)}
    result = await db.analyses.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.contracts.update_one({"_id": contract["_id"]}, {"$set": {"latest_analysis_id": str(result.inserted_id), "analysis_summary": analysis, "updated_at": datetime.now(timezone.utc)}})
    return analysis
