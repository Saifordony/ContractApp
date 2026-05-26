from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.services.contract_intelligence import chunk_contract_text

NOISE_KEYWORDS = {
    "experience", "skills", "agile", "git", "qualifications", "responsibilities",
    "job description", "requirements", "resume", "cv", "candidate", "education",
}

DOC_TYPE_KEYWORDS = {
    "employment_contract": {"employee", "employer", "salary", "probation", "leave", "termination"},
    "service_agreement": {"services", "deliverables", "client", "vendor", "statement of work"},
    "nda": {"confidential", "non-disclosure", "disclosing party", "receiving party"},
    "lease": {"tenant", "landlord", "rent", "premises", "lease"},
    "sales_agreement": {"buyer", "seller", "purchase", "goods", "delivery", "invoice"},
}

CLAUSE_LIBRARY = {
    "employment_contract": {
        "parties": ["between", "employer", "employee", "party a", "party b", "company", "contractor", "client", "supplier"],
        "role_position": ["position", "role", "job title"],
        "start_date": ["start date", "effective date", "commencement"],
        "work_location": ["work location", "location", "workplace", "remote"],
        "compensation": ["salary", "compensation", "wage", "payment"],
        "benefits": ["benefits", "insurance", "allowance"],
        "working_hours": ["working hours", "hours per week", "overtime"],
        "probation": ["probation"],
        "leave_policy": ["leave", "vacation", "annual leave", "sick leave"],
        "confidentiality": ["confidential", "non-disclosure"],
        "ip_assignment": ["intellectual property", "ip", "assignment"],
        "termination": ["termination", "terminate"],
        "notice_period": ["notice period", "notice"],
        "governing_law": ["governing law", "laws of", "jurisdiction"],
        "dispute_resolution": ["dispute", "arbitration", "mediation", "court"],
        "non_compete": ["non-compete", "non solicitation", "non-solicit"],
    },
    "service_agreement": {
        "parties": ["between", "client", "supplier", "vendor", "contractor"],
        "scope_of_work": ["scope", "services", "statement of work"],
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
        "parties": ["between", "party"],
        "scope": ["scope", "services"],
        "payment_terms": ["payment", "invoice"],
        "termination": ["termination", "terminate"],
        "governing_law": ["governing law", "jurisdiction"],
        "dispute_resolution": ["dispute", "arbitration", "court"],
        "confidentiality": ["confidential", "non-disclosure"],
    },
}

WHY_IT_MATTERS = {
    "parties": "Identifies who is legally bound by the contract and each party's role.",
    "compensation": "Defines financial obligations and reduces payment disputes.",
}


def _pretty(name: str) -> str:
    return name.replace("_", " ").title()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def detect_document_type(contract_text: str) -> Dict[str, Any]:
    text = (contract_text or "").lower()
    noise_hits = sum(1 for kw in NOISE_KEYWORDS if kw in text)
    scores = {k: sum(1 for kw in kws if kw in text) for k, kws in DOC_TYPE_KEYWORDS.items()}
    best_type = max(scores, key=scores.get) if scores else "unknown"
    best_score = scores.get(best_type, 0)
    warnings: List[str] = []

    if noise_hits >= 4 and best_score <= 2:
        doc_type = "cv_or_job_description"
        confidence = 0.9
        warnings.append("Document appears to be a CV/job description. Legal clause extraction was limited.")
    elif best_score == 0:
        doc_type = "unknown"
        confidence = 0.35
    else:
        doc_type = best_type
        confidence = min(0.95, 0.55 + (best_score * 0.08))

    if noise_hits >= 2 and doc_type != "cv_or_job_description":
        warnings.append("Some sections appear to contain job-description or CV-style text. These sections were excluded from clause classification unless legally relevant.")

    return {
        "document_type": doc_type,
        "document_type_confidence": round(confidence, 2),
        "warnings": warnings,
    }


def _is_valid_parties_text(text: str) -> bool:
    lower = text.lower()
    party_markers = ["between", "employer", "employee", "client", "supplier", "party a", "party b", "company", "contractor"]
    contamination = ["experience", "skills", "agile", "git", "responsibilities", "requirements", "resume", "cv"]
    if any(m in lower for m in contamination) and not any(m in lower for m in party_markers):
        return False
    return any(m in lower for m in party_markers)


def _confidence_for_text(text: str) -> float:
    l = len(text)
    if l > 180:
        return 0.88
    if l > 80:
        return 0.72
    if l > 25:
        return 0.55
    return 0.3


def extract_clauses_with_validation(contract_text: str) -> Dict[str, Any]:
    clean_text = _normalize_text(contract_text)
    doc_info = detect_document_type(clean_text)
    clause_set = CLAUSE_LIBRARY.get(doc_info["document_type"], CLAUSE_LIBRARY["unknown"])
    chunks = chunk_contract_text(contract_text)

    clause_cards: List[Dict[str, Any]] = []
    for clause_key, keywords in clause_set.items():
        matches = []
        for chunk in chunks:
            lower = chunk.text.lower()
            if any(k in lower for k in keywords):
                matches.append({"quote": chunk.text[:260], "location": chunk.location, "reason": f"Contains keywords for {_pretty(clause_key)}."})

        status = "not_found"
        extracted_text = None
        confidence = 0.0
        issues: List[str] = []

        if matches:
            extracted_text = matches[0]["quote"]
            confidence = _confidence_for_text(extracted_text)
            status = "found" if confidence >= 0.7 else "partially_found"

            if clause_key == "parties" and not _is_valid_parties_text(extracted_text):
                status = "not_found"
                extracted_text = None
                confidence = 0.0
                issues.append("The extracted text did not identify actual contracting parties.")

        clause_cards.append({
            "clause_key": clause_key,
            "clause_name": _pretty(clause_key),
            "status": status,
            "confidence": round(confidence, 2),
            "extracted_text": extracted_text,
            "plain_english_summary": extracted_text[:180] if extracted_text else "Clause not found in the provided contract text.",
            "why_it_matters": WHY_IT_MATTERS.get(clause_key, f"{_pretty(clause_key)} helps define legal obligations and reduce ambiguity."),
            "evidence_snippets": matches[:2] if extracted_text else [],
            "issues": issues,
            "recommended_action": "Add a clear clause with explicit legal wording and responsibilities." if status == "not_found" else "Review wording for completeness and clarity.",
        })

    return {
        "document_type": doc_info["document_type"],
        "document_type_confidence": doc_info["document_type_confidence"],
        "warnings": doc_info["warnings"],
        "clause_results": clause_cards,
    }
