from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


NOISE_KEYWORDS = {
    "experience", "skills", "agile", "git", "qualifications", "responsibilities",
    "job description", "requirements", "resume", "cv", "candidate", "education",
    "communication skills", "problem-solving",
}

LEGAL_HEADINGS = {
    "parties", "compensation", "salary", "payment", "termination", "confidentiality",
    "working hours", "leave", "governing law", "dispute resolution", "intellectual property", "probation",
}

DOC_TYPE_KEYWORDS = {
    "employment_contract": {"employee", "employer", "salary", "probation", "leave", "termination"},
    "service_agreement": {"services", "deliverables", "client", "vendor", "statement of work"},
    "nda": {"confidential", "non-disclosure", "disclosing party", "receiving party"},
    "lease": {"tenant", "landlord", "rent", "premises", "lease"},
    "sales_agreement": {"buyer", "seller", "purchase", "goods", "delivery", "invoice"},
}

CLAUSE_LIBRARY: Dict[str, Dict[str, List[str]]] = {
    "employment_contract": {
        "parties": ["between", "employer", "employee", "party a", "party b", "company", "contractor", "client", "supplier", "represented by"],
        "employer_details": ["employer", "company", "registered office"],
        "employee_details": ["employee", "passport", "id number"],
        "role_position": ["position", "role", "job title"],
        "start_date": ["start date", "effective date", "commencement"],
        "work_location": ["work location", "location", "workplace", "remote"],
        "compensation": ["salary", "compensation", "wage", "payment", "monthly pay", "remuneration", "allowance"],
        "benefits": ["benefits", "insurance", "allowance"],
        "working_hours": ["working hours", "work schedule", "hours per week", "overtime", "working days"],
        "probation": ["probation"],
        "leave_policy": ["annual leave", "vacation", "sick leave", "public holidays", "paid leave"],
        "confidentiality": ["confidential", "confidentiality", "non-disclosure", "proprietary information"],
        "ip_assignment": ["intellectual property", "ip", "assignment"],
        "termination": ["termination", "terminate", "end of employment", "dismissal", "resignation"],
        "notice_period": ["notice period", "written notice", "days notice"],
        "governing_law": ["governing law", "jurisdiction", "laws of", "courts of"],
        "dispute_resolution": ["dispute", "arbitration", "mediation", "court"],
        "non_compete": ["non-compete", "non solicitation", "non-solicit"],
    },
    "service_agreement": {
        "parties": ["between", "client", "supplier", "vendor", "contractor", "represented by"],
        "scope_of_work": ["scope of work", "services", "statement of work"],
        "deliverables": ["deliverables", "milestones"],
        "fees_payment_terms": ["fees", "payment", "invoice", "price"],
        "timeline": ["timeline", "term", "schedule", "duration"],
        "acceptance_criteria": ["acceptance", "sign off"],
        "confidentiality": ["confidential", "non-disclosure"],
        "ip_ownership": ["intellectual property", "ownership", "license"],
        "liability": ["liability", "damages", "cap"],
        "indemnity": ["indemnif"],
        "termination": ["termination", "terminate"],
        "governing_law": ["governing law", "jurisdiction"],
        "dispute_resolution": ["dispute", "arbitration", "mediation"],
    },
    "nda": {
        "parties": ["between", "disclosing", "receiving"],
        "definition_of_confidential_information": ["confidential information", "definition"],
        "obligations": ["obligation", "shall not disclose"],
        "exclusions": ["exclusion", "not confidential"],
        "duration": ["term", "duration"],
        "permitted_disclosure": ["permitted", "required by law"],
        "return_destruction": ["return", "destroy"],
        "remedies": ["remedies", "injunctive"],
        "governing_law": ["governing law", "jurisdiction"],
        "dispute_resolution": ["dispute", "arbitration", "mediation"],
    },
    "unknown": {
        "parties": ["between", "party"], "compensation": ["salary", "payment"], "termination": ["termination", "notice"],
        "governing_law": ["governing law", "jurisdiction"], "confidentiality": ["confidential", "non-disclosure"],
    },
}

@dataclass
class ContractChunk:
    chunk_id: str
    heading: str
    text: str
    start_char: int
    end_char: int
    page: Optional[int] = None


def _pretty(name: str) -> str:
    return name.replace("_", " ").title()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def segment_contract_text(raw_text: str) -> List[ContractChunk]:
    lines = (raw_text or "").splitlines()
    chunks: List[ContractChunk] = []
    current: List[str] = []
    heading = "General"
    start = 0
    cursor = 0
    idx = 1

    def is_heading(line: str) -> bool:
        s = line.strip()
        if not s:
            return False
        if re.match(r"^(\d+\.?|\d+\.\d+|article\s+\d+|section\s+\d+)", s.lower()):
            return True
        if s.upper() == s and 3 <= len(s) <= 90:
            return True
        return any(h in s.lower() for h in LEGAL_HEADINGS)

    def flush(end_pos: int):
        nonlocal idx, current, start
        txt = "\n".join(current).strip()
        if txt:
            chunks.append(ContractChunk(f"chunk_{idx:03d}", heading, txt, start, end_pos, None))
            idx += 1
        current = []

    for line in lines:
        ll = len(line) + 1
        if is_heading(line) and current:
            flush(cursor)
            heading = line.strip()[:80]
            start = cursor
        elif is_heading(line):
            heading = line.strip()[:80]
            start = cursor
        current.append(line)
        if len("\n".join(current).split()) >= 950:
            flush(cursor + ll)
            start = cursor + ll
        cursor += ll

    if current:
        flush(cursor)

    if not chunks:
        text = _normalize_text(raw_text)
        words = text.split()
        step = 850
        overlap = 150
        c = 1
        i = 0
        while i < len(words):
            part = words[i:i + step]
            chunk_text = " ".join(part)
            chunks.append(ContractChunk(f"chunk_{c:03d}", "General", chunk_text, i, i + len(part), None))
            c += 1
            i += max(1, step - overlap)
    return chunks


def detect_document_type(contract_text: str) -> Dict[str, Any]:
    text = (contract_text or "").lower()
    noise_hits = sum(1 for kw in NOISE_KEYWORDS if kw in text)
    scores = {k: sum(1 for kw in kws if kw in text) for k, kws in DOC_TYPE_KEYWORDS.items()}
    best_type = max(scores, key=scores.get) if scores else "unknown"
    best_score = scores.get(best_type, 0)
    contamination_score = min(1.0, noise_hits / 10)
    warnings: List[str] = []
    if contamination_score >= 0.25:
        warnings.append("This document contains CV/job-description-style text. The extractor ignored unrelated skills/requirements text unless directly relevant to a contract clause.")
    if noise_hits >= 5 and best_score <= 2:
        doc_type = "cv_or_job_description"
        confidence = 0.9
    elif best_score == 0:
        doc_type = "unknown"
        confidence = 0.35
    else:
        doc_type = best_type
        confidence = min(0.95, 0.55 + (best_score * 0.08))
    return {"document_type": doc_type, "document_type_confidence": round(confidence, 2), "contamination_score": round(contamination_score, 2), "warnings": warnings}


def _candidate_chunks(clause_key: str, keywords: List[str], chunks: List[ContractChunk]) -> List[Dict[str, Any]]:
    scored = []
    for c in chunks:
        txt = c.text.lower()
        heading = c.heading.lower()
        key_hits = sum(2 for k in keywords if k in txt)
        heading_hits = sum(3 for k in keywords if k in heading)
        score = key_hits + heading_hits
        if score > 0:
            scored.append({"chunk": c, "score": score, "matched_keywords": [k for k in keywords if k in txt or k in heading], "matched_heading": c.heading})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:5]


def _llm_verify_clause(clause_key: str, clause_name: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    llm_model = None
    try:
        from backend.gen1 import llm_model as _model
        llm_model = _model
    except Exception:
        llm_model = None
    candidate_payload = [{"chunk_id": x["chunk"].chunk_id, "heading": x["chunk"].heading, "text": x["chunk"].text[:1800]} for x in candidates]
    prompt = f"""
You are not filling a checklist. You are verifying whether provided candidate text contains a specific legal clause.
You must answer only based on provided candidate text. If not explicit, return not_found.
Do not infer. Do not guess. Do not use general contract knowledge.
Do not classify CV/job-description/skills text as contract clauses.
Evidence quote is mandatory for found or partially_found.
Return valid JSON only.
Clause key: {clause_key}
Clause name: {clause_name}
Candidate text JSON: {json.dumps(candidate_payload)}
Output schema keys: clause_key, clause_name, status, confidence, extracted_text, plain_english_summary, why_it_matters, evidence_snippets, issues, recommended_action
"""
    try:
        if llm_model is None:
            return {}
        raw = llm_model.invoke(prompt).content
        text = str(raw).strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        if "{" in text and "}" in text:
            text = text[text.find("{"):text.rfind("}")+1]
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _reject_noise(text: str) -> bool:
    lower = (text or "").lower()
    hits = sum(1 for kw in NOISE_KEYWORDS if kw in lower)
    return hits >= 2


def _validate_clause(clause_key: str, card: Dict[str, Any]) -> Dict[str, Any]:
    text = (card.get("extracted_text") or "").lower()
    issues = list(card.get("issues", []))
    status = card.get("status", "not_found")
    if status in {"found", "partially_found", "needs_review"} and not card.get("evidence_snippets"):
        status = "not_found"; card["extracted_text"] = None; card["confidence"] = 0.0; issues.append("Validation rejected extraction: missing direct evidence quote.")

    if clause_key == "parties":
        party_patterns = [r"between\s+.+\s+and\s+.+", r"employer\s*:\s*", r"employee\s*:\s*", r"client\s*:\s*", r"contractor\s*:\s*", r"party\s*a", r"party\s*b"]
        if _reject_noise(text) or not any(re.search(p, text) for p in party_patterns):
            status = "not_found"; card["extracted_text"] = None; card["confidence"] = 0.0; issues.append("The extracted text did not identify actual contracting parties.")
    if clause_key == "compensation" and status != "not_found":
        if not any(k in text for k in ["salary", "payment", "jod", "usd", "monthly", "wage", "remuneration", "allowance"]):
            status = "needs_review"; card["confidence"] = min(card.get("confidence", 0.0), 0.4); issues.append("Compensation evidence is too generic and lacks payment obligation details.")
    if clause_key == "termination" and status != "not_found":
        if not any(k in text for k in ["terminate", "termination", "notice", "resignation", "dismissal"]):
            status = "needs_review"; issues.append("Termination clause lacks clear rights, grounds, or notice process.")
    if clause_key == "governing_law" and status != "not_found":
        if not any(k in text for k in ["governing law", "jurisdiction", "laws of", "courts of"]):
            status = "not_found"; card["extracted_text"] = None; card["confidence"] = 0.0; issues.append("No governing-law or jurisdiction wording found.")
    if clause_key == "leave_policy" and status != "not_found":
        if not any(k in text for k in ["annual leave", "vacation", "sick leave", "public holiday", "paid leave"]):
            status = "not_found"; card["extracted_text"] = None; card["confidence"] = 0.0; issues.append("No leave entitlement evidence found.")

    card["status"] = status
    card["issues"] = issues
    if status == "not_found":
        card["extracted_text"] = None
        card["evidence_snippets"] = []
        card["plain_english_summary"] = "No reliable evidence found in the contract."
    return card


def extract_clauses_with_validation(contract_text: str, extraction_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    clean_text = _normalize_text(contract_text)
    doc_info = detect_document_type(clean_text)
    chunks = segment_contract_text(contract_text)
    clause_set = CLAUSE_LIBRARY.get(doc_info["document_type"], CLAUSE_LIBRARY["unknown"])

    clause_cards: List[Dict[str, Any]] = []
    for clause_key, keywords in clause_set.items():
        candidates = _candidate_chunks(clause_key, keywords, chunks)
        if not candidates:
            card = {
                "clause_key": clause_key, "clause_name": _pretty(clause_key), "status": "not_found", "confidence": 0.0,
                "extracted_text": None, "plain_english_summary": "No reliable evidence found in the contract.",
                "why_it_matters": f"{_pretty(clause_key)} helps define legal obligations and reduce ambiguity.",
                "evidence_snippets": [], "issues": ["No candidate chunks matched clause keywords."],
                "recommended_action": "Add a clear clause with explicit legal wording and responsibilities.",
                "debug": {"matched_heading": None, "matched_keywords": [], "validation_result": "not_found"},
            }
            clause_cards.append(card)
            continue

        llm_result = _llm_verify_clause(clause_key, _pretty(clause_key), candidates)
        top = candidates[0]
        default_text = top["chunk"].text[:320]
        card = {
            "clause_key": clause_key,
            "clause_name": _pretty(clause_key),
            "status": llm_result.get("status", "partially_found"),
            "confidence": float(llm_result.get("confidence", min(0.8, 0.35 + top["score"] / 12))),
            "extracted_text": llm_result.get("extracted_text") or default_text,
            "plain_english_summary": llm_result.get("plain_english_summary") or default_text[:180],
            "why_it_matters": llm_result.get("why_it_matters") or f"{_pretty(clause_key)} helps define legal obligations and reduce ambiguity.",
            "evidence_snippets": llm_result.get("evidence_snippets") or [{"quote": default_text[:220], "chunk_id": top["chunk"].chunk_id, "reason": "Top candidate chunk matched keywords."}],
            "issues": llm_result.get("issues") or [],
            "recommended_action": llm_result.get("recommended_action") or "Review wording for completeness and clarity.",
            "debug": {"matched_heading": top["matched_heading"], "matched_keywords": top["matched_keywords"], "validation_result": "pending"},
        }
        card = _validate_clause(clause_key, card)
        card["debug"]["validation_result"] = card["status"]
        clause_cards.append(card)

    detected_headings = [c.heading for c in chunks[:20]]
    text_warnings = list(doc_info.get("warnings", []))
    if extraction_metadata and extraction_metadata.get("raw_text_length", 0) < 500:
        text_warnings.append("The document text extraction appears incomplete. Try OCR mode or upload a clearer PDF.")

    return {
        "document_type": doc_info["document_type"],
        "document_type_confidence": doc_info["document_type_confidence"],
        "contamination_score": doc_info["contamination_score"],
        "warnings": text_warnings,
        "detected_headings": detected_headings,
        "chunks": [asdict(c) for c in chunks[:30]],
        "clause_results": clause_cards,
    }
