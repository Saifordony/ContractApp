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


TERM_PATTERNS = {
    "Contract type": ["employment", "service agreement", "lease", "purchase", "subscription", "consulting"],
    "Parties": ["between", "employer", "employee", "client", "contractor"],
    "Role / scope": ["position", "role", "scope", "services", "duties"],
    "Start date": ["commencement", "start date", "effective date", "begins"],
    "Salary / payment": ["salary", "compensation", "payment", "fees", "invoice"],
    "Working hours": ["working hours", "hours of work", "work hours"],
    "Annual leave": ["annual leave", "vacation", "paid leave"],
    "Probation": ["probation", "probationary"],
    "Termination": ["termination", "terminate"],
    "Confidentiality": ["confidential", "non-disclosure"],
    "Intellectual property": ["intellectual property", "work product", "ownership"],
    "Non-compete / non-solicitation": ["non-compete", "non compete", "non-solicitation", "non solicitation"],
    "Governing law / dispute resolution": ["governing law", "jurisdiction", "dispute", "arbitration", "mediation"],
}

DETAIL_REGEX = {
    "monetary_amounts": r"(?:SAR|USD|AED|EUR|GBP|ر\.س|﷼|\$)\s?[0-9][0-9,]*(?:\.\d+)?|[0-9][0-9,]*(?:\.\d+)?\s?(?:SAR|USD|AED|EUR|GBP|riyal|riyals|dollars)",
    "dates": r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b",
    "durations": r"\b\d+\s+(?:day|days|working days|week|weeks|month|months|year|years)\b",
    "notice_periods": r"\b\d+\s+(?:day|days|working days|week|weeks|month|months)\s+(?:notice|prior notice|written notice)\b",
    "payment_timing": r"\b(?:monthly|annually|quarterly|in arrears|in advance|last working day|within \d+ days|due upon receipt)\b",
}


def _clean_snippet(value: str, max_len: int = 520) -> str:
    return " ".join((value or "").split())[:max_len]


def _extract_matches(pattern: str, text: str, limit: int = 6) -> list[str]:
    import re
    seen = []
    for match in re.findall(pattern, text or "", flags=re.IGNORECASE):
        item = match if isinstance(match, str) else " ".join(match)
        item = _clean_snippet(item, 120)
        if item and item.lower() not in {x.lower() for x in seen}:
            seen.append(item)
        if len(seen) >= limit:
            break
    return seen


def _details_from_evidence(clause_type: str, evidence_text: str) -> dict[str, Any]:
    details = {name: _extract_matches(pattern, evidence_text) for name, pattern in DETAIL_REGEX.items()}
    lower = evidence_text.lower()
    details["responsible_parties"] = [label for label in ["Employer", "Employee", "Client", "Contractor", "Either party"] if label.lower() in lower]
    details["obligations"] = _extract_matches(r"(?:shall|must|is required to|agrees to|will)\s+[^.;]{8,180}", evidence_text, 4)
    details["rights"] = _extract_matches(r"(?:may|is entitled to|has the right to)\s+[^.;]{8,180}", evidence_text, 4)
    details["restrictions"] = _extract_matches(r"(?:shall not|must not|may not|prohibited from|without prior)\s+[^.;]{8,180}", evidence_text, 4)
    details["conditions"] = _extract_matches(r"(?:subject to|provided that|if|unless)\s+[^.;]{8,180}", evidence_text, 4)
    details["exceptions"] = _extract_matches(r"(?:except|excluding|other than|unless)\s+[^.;]{8,160}", evidence_text, 3)
    details["survival_language"] = _extract_matches(r"surviv(?:e|al)[^.;]{0,180}", evidence_text, 3)
    details["penalties_or_consequences"] = _extract_matches(r"(?:penalt(?:y|ies)|deduct(?:ion|ions)?|damages|forfeit|terminate|withhold)[^.;]{0,180}", evidence_text, 4)
    details["related_clauses"] = [item for item, terms in CLAUSE_PATTERNS.items() if item != clause_type and any(term in lower for term in terms)]
    return {key: value for key, value in details.items() if value}


def _human_clause_fields(clause_type: str, status: str, details: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, str]:
    has_evidence = bool(evidence)
    detail_bits = []
    for label, key in [("amounts", "monetary_amounts"), ("timing", "payment_timing"), ("dates", "dates"), ("durations", "durations"), ("notice", "notice_periods")]:
        if details.get(key):
            detail_bits.append(f"{label}: {', '.join(details[key][:3])}")
    detail_sentence = f" Key extracted details include {('; '.join(detail_bits))}." if detail_bits else ""
    label = clause_type.replace("_", " ")
    if status == "missing":
        return {
            "simple_explanation": f"The review did not find clear contract text for a {label} clause.",
            "why_it_matters": f"A {label} clause helps the parties understand this important part of the deal before they rely on the contract.",
            "risk_in_plain_english": f"If the {label} position is missing or unclear, the parties may disagree later about rights, obligations, timing, or remedies.",
            "what_to_check_next": f"Ask the business owner or counsel whether a {label} clause should be added for this transaction.",
            "negotiation_note": f"Negotiate clear, deal-specific {label} language if this topic matters to either party.",
            "completeness": "Missing",
        }
    return {
        "simple_explanation": f"This clause appears to address {label} in the contract.{detail_sentence}",
        "why_it_matters": f"It matters because it defines how {label} works in practice and who must do what.",
        "risk_in_plain_english": "The main risk is that important details may still be incomplete, one-sided, or hard to enforce if they are not clearly stated in the evidence.",
        "what_to_check_next": "Confirm the extracted details, any approval steps, deadlines, exceptions, and consequences with the responsible business or legal reviewer.",
        "negotiation_note": "If the clause affects money, timing, ownership, termination, or restrictions, negotiate clearer limits, responsibilities, and exceptions.",
        "completeness": "Strong" if has_evidence and len(details) >= 3 else "Partial",
    }


def _confidence_label(status: str, details: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    if status == "missing":
        return "Low — no direct evidence was found in the extracted text."
    if evidence and len(details) >= 2:
        return "High — clear evidence and multiple useful details were extracted."
    if evidence:
        return "Medium — evidence was found, but some important details are not visible in the snippet."
    return "Low — only weak or indirect evidence was found."


def _term_explanation(name: str, value: str) -> tuple[str, str]:
    lower = name.lower()
    if "leave" in lower:
        return ("This explains paid time off and whether approval is needed before taking leave.", "Confirm current leave balance, approval process, carry-over, and special leave rules.")
    if "salary" in lower or "payment" in lower:
        return ("This explains compensation or payment mechanics such as amount, timing, and method.", "Confirm gross/net amount, due date, deductions, final settlement, and dispute handling.")
    if "termination" in lower:
        return ("This explains how the contract can end and what notice or reasons may be required.", "Confirm notice periods, termination for cause, cure periods, and post-termination obligations.")
    if "intellectual" in lower:
        return ("This explains who owns work product, inventions, code, documents, or other IP created under the relationship.", "Confirm treatment of pre-existing work, side projects, licenses, and work created outside the role.")
    if "non-compete" in lower:
        return ("This explains restrictions on competing with or soliciting people connected to the business.", "Confirm duration, geography, scope, enforceability, and whether restrictions are reasonable.")
    if "parties" in lower:
        return ("This identifies who the contract appears to bind.", "Confirm legal names, signing entities, and authority to sign.")
    return ("This is a key business term extracted from the contract evidence.", "Confirm the extracted value against the original signed document.")


def _extract_key_terms(text: str, clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    terms = []
    for name, keywords in TERM_PATTERNS.items():
        evidence = _evidence_for(text, keywords)
        if not evidence:
            continue
        snippet = evidence[0]["text"]
        details = _details_from_evidence(name.lower().replace(" / ", "_").replace(" ", "_"), snippet)
        extracted = []
        for key in ["monetary_amounts", "payment_timing", "dates", "durations", "notice_periods", "responsible_parties", "obligations", "rights", "conditions"]:
            if details.get(key):
                extracted.extend(details[key][:2])
        value = "; ".join(extracted[:4]) or _clean_snippet(snippet, 180)
        explanation, verify = _term_explanation(name, value)
        terms.append({
            "term": name,
            "extracted_value": value,
            "evidence": evidence,
            "evidence_source": evidence[0].get("source", "extracted_text"),
            "simple_explanation": explanation,
            "risk_or_verify": verify,
            "confidence": _confidence_label("found", details, evidence),
        })
    return terms[:12]


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
        evidence_text = evidence[0]["text"] if evidence else ""
        details = _details_from_evidence(key, evidence_text)
        status = "found" if evidence and len(details) >= 2 else "partial" if evidence else "missing" if key in CRITICAL else "partial"
        human = _human_clause_fields(key, status, details, evidence)
        confidence = _confidence_label(status, details, evidence)
        clauses.append({
            "type": key,
            "title": key.replace("_", " ").title(),
            "status": status,
            "found": bool(evidence),
            "confidence": confidence,
            "evidence": evidence,
            "extracted_details": details,
            "parties_involved": details.get("responsible_parties", []),
            "obligations": details.get("obligations", []),
            "rights": details.get("rights", []),
            "restrictions": details.get("restrictions", []),
            "deadlines": details.get("dates", []),
            "notice_periods": details.get("notice_periods", []),
            "monetary_amounts": details.get("monetary_amounts", []),
            "payment_timing": details.get("payment_timing", []),
            "durations": details.get("durations", []),
            "conditions": details.get("conditions", []),
            "exceptions": details.get("exceptions", []),
            "survival_language": details.get("survival_language", []),
            "penalties_or_consequences": details.get("penalties_or_consequences", []),
            "related_clauses": details.get("related_clauses", []),
            "rule_based_summary": "Precise evidence and key details were extracted from the contract text." if evidence else "No direct evidence was found in the extracted contract text.",
            **human,
        })
    missing = [c for c in CRITICAL if not next(item for item in clauses if item["type"] == c)["found"]]
    found_count = sum(1 for c in clauses if c["found"])
    detail_bonus = sum(1 for c in clauses if c.get("extracted_details"))
    score = max(15, min(100, int((found_count / len(CLAUSE_PATTERNS) * 82) + min(18, detail_bonus * 2)))) if text else 0
    risks = []
    for miss in missing:
        risks.append({"severity": "high" if miss in ["liability", "termination"] else "medium", "title": f"Missing {miss.replace('_',' ')} clause", "affected_clause": miss, "explanation": f"The extracted text does not show a clear {miss.replace('_',' ')} clause, so rights, obligations, or remedies may be uncertain.", "suggested_mitigation": f"Add deal-specific {miss.replace('_',' ')} language or confirm why it is not needed."})
    key_terms = _extract_key_terms(text, clauses)
    return {"clauses": clauses, "key_terms": key_terms, "missing_critical_clauses": missing, "health_score": score, "risk_level": "High" if score < 55 else "Medium" if score < 80 else "Low", "risks": risks}


def _fallback_ai_fields(rule_result: dict[str, Any], status: str, parse_failed: bool = False, error: str | None = None) -> dict[str, Any]:
    missing = rule_result["missing_critical_clauses"]
    clauses = []
    for clause in rule_result["clauses"]:
        human = _human_clause_fields(clause["type"], clause["status"], clause.get("extracted_details", {}), clause.get("evidence", []))
        if clause["found"]:
            insight = human["why_it_matters"]
            recommendation = human["what_to_check_next"]
            priority = "High" if clause["status"] == "partial" and clause["type"] in CRITICAL else "Medium"
            risk_text = human["risk_in_plain_english"]
        else:
            insight = human["why_it_matters"]
            recommendation = human["what_to_check_next"]
            priority = "High" if clause["type"] in CRITICAL else "Medium"
            risk_text = human["risk_in_plain_english"]
        clauses.append({**clause, **human, "ai_insight": insight, "ai_risk_assessment": risk_text, "ai_recommendation": recommendation, "negotiation_note": human["negotiation_note"], "review_priority": priority})
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
        "recommended_actions": [r["suggested_mitigation"] for r in rule_result["risks"]] or ["Review the extracted key terms, confirm business assumptions, and complete human legal review before signature."],
        "key_terms": rule_result.get("key_terms", []),
        "clauses": clauses,
        "raw_llm_response": {},
    }


def _ai_prompt(text: str, rule_result: dict[str, Any]) -> str:
    evidence_payload = json.dumps(rule_result, default=str)[:12000]
    contract_excerpt = text[:16000]
    return f"""
Review the following contract as an AI contract review assistant. Use only the contract text, extracted clauses, evidence snippets, missing clause results, and rule-based health score provided. Do not invent facts. Do not provide final legal advice. Use language like AI review, risk signal, and recommended review point. Return structured JSON only.

Required JSON keys: executive_summary, ai_overall_assessment, key_strengths, key_risks, missing_clauses, recommended_actions, clauses, key_terms.
For each clause, use only the provided contract text and evidence. Explain the clause in simple language for a business user. Avoid legal jargon. Do not provide final legal advice.
Each item in clauses must include: type, simple_explanation, why_it_matters, risk_in_plain_english, what_to_check_next, ai_insight, ai_risk_assessment, ai_recommendation, negotiation_note, review_priority, completeness, confidence.
Each key term may include: term, extracted_value, simple_explanation, risk_or_verify, confidence.
If evidence is weak or missing, say clearly that the contract text provided does not show enough evidence to confirm the point.

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
        human = _human_clause_fields(clause["type"], clause["status"], clause.get("extracted_details", {}), clause.get("evidence", []))
        clauses.append({
            **clause,
            "simple_explanation": ai_clause.get("simple_explanation") or human["simple_explanation"],
            "why_it_matters": ai_clause.get("why_it_matters") or human["why_it_matters"],
            "risk_in_plain_english": ai_clause.get("risk_in_plain_english") or human["risk_in_plain_english"],
            "what_to_check_next": ai_clause.get("what_to_check_next") or human["what_to_check_next"],
            "completeness": ai_clause.get("completeness") or human["completeness"],
            "ai_insight": ai_clause.get("ai_insight") or ai_clause.get("why_it_matters") or human["why_it_matters"],
            "ai_risk_assessment": ai_clause.get("ai_risk_assessment") or ai_clause.get("risk_in_plain_english") or human["risk_in_plain_english"],
            "ai_recommendation": ai_clause.get("ai_recommendation") or ai_clause.get("what_to_check_next") or human["what_to_check_next"],
            "negotiation_note": ai_clause.get("negotiation_note") or human["negotiation_note"],
            "review_priority": ai_clause.get("review_priority") or ("High" if clause["type"] in rule_result["missing_critical_clauses"] else "Medium"),
            "confidence": ai_clause.get("confidence") or clause.get("confidence") or _confidence_label(clause["status"], clause.get("extracted_details", {}), clause.get("evidence", [])),
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
                "key_terms": raw_ai.get("key_terms") or rule_result.get("key_terms", []),
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
        "key_terms": ai_fields.get("key_terms") or rule_result.get("key_terms", []),
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
