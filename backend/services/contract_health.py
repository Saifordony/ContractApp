from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


CONTRACT_TYPE_RULES: Dict[str, Dict[str, Any]] = {
    "employment": {
        "keywords": ["employee", "employer", "salary", "probation", "benefits"],
        "required": [
            "compensation",
            "working_hours",
            "termination",
            "confidentiality",
            "governing_law",
        ],
        "recommended": ["non_compete", "ip_assignment", "leave_policy"],
    },
    "service_agreement": {
        "keywords": ["services", "deliverables", "statement of work", "client", "vendor"],
        "required": [
            "scope_of_work",
            "payment_terms",
            "acceptance_criteria",
            "termination",
            "limitation_of_liability",
            "confidentiality",
            "governing_law",
            "dispute_resolution",
        ],
        "recommended": ["change_control", "sla", "indemnification", "audit_rights"],
    },
    "nda": {
        "keywords": ["confidential", "non-disclosure", "receiving party", "disclosing party"],
        "required": ["confidentiality", "term", "permitted_use", "remedies", "governing_law"],
        "recommended": ["exceptions", "return_or_destroy", "injunctive_relief"],
    },
    "lease": {
        "keywords": ["tenant", "landlord", "rent", "premises", "lease term"],
        "required": ["rent", "term", "maintenance", "default", "termination", "governing_law"],
        "recommended": ["security_deposit", "renewal", "insurance"],
    },
    "general_commercial": {
        "keywords": [],
        "required": [
            "scope_of_work",
            "payment_terms",
            "termination",
            "limitation_of_liability",
            "governing_law",
            "dispute_resolution",
        ],
        "recommended": ["confidentiality", "indemnification", "force_majeure", "notice"],
    },
}

CLAUSE_KEYWORDS: Dict[str, List[str]] = {
    "scope_of_work": ["scope", "deliverable", "services"],
    "payment_terms": ["payment", "invoice", "fee", "price", "compensation"],
    "acceptance_criteria": ["acceptance", "milestone", "sign off"],
    "termination": ["termination", "terminate", "expiry", "end of term"],
    "limitation_of_liability": ["liability", "damages", "cap", "without limitation", "unlimited"],
    "confidentiality": ["confidential", "non-disclosure"],
    "governing_law": ["governing law", "laws of", "jurisdiction"],
    "dispute_resolution": ["dispute", "arbitration", "mediation", "court"],
    "change_control": ["change order", "amendment", "modification"],
    "sla": ["sla", "service level", "uptime", "response time"],
    "indemnification": ["indemnif"],
    "audit_rights": ["audit", "inspection rights"],
    "working_hours": ["working hours", "hours per week"],
    "non_compete": ["non-compete", "non solicitation", "non-solicitation"],
    "ip_assignment": ["intellectual property", "work product", "assign"],
    "leave_policy": ["leave", "vacation", "sick leave"],
    "term": ["term", "duration", "effective date"],
    "permitted_use": ["permitted use", "purpose"],
    "remedies": ["remedies", "injunctive"],
    "exceptions": ["exceptions"],
    "return_or_destroy": ["return", "destroy"],
    "injunctive_relief": ["injunctive"],
    "rent": ["rent"],
    "maintenance": ["maintenance", "repair"],
    "default": ["default", "breach"],
    "security_deposit": ["security deposit"],
    "renewal": ["renewal", "auto renew"],
    "insurance": ["insurance"],
    "force_majeure": ["force majeure"],
    "notice": ["notice"],
    "compensation": ["salary", "compensation"],
}




def _is_arabic_response(response_language: str) -> bool:
    lang = (response_language or "english").strip().lower()
    return lang in {"arabic", "ar", "ara", "العربية", "arab"}


def _msg(en: str, ar: str, response_language: str) -> str:
    return ar if _is_arabic_response(response_language) else en


def _pretty_clause_name(name: str, response_language: str) -> str:
    arabic_map = {
        "scope_of_work": "نطاق العمل",
        "payment_terms": "شروط الدفع",
        "acceptance_criteria": "معايير القبول",
        "termination": "الإنهاء",
        "limitation_of_liability": "تحديد المسؤولية",
        "confidentiality": "السرية",
        "governing_law": "القانون الواجب التطبيق",
        "dispute_resolution": "فض النزاعات",
        "change_control": "إدارة التغييرات",
        "sla": "مستويات الخدمة",
        "indemnification": "التعويض",
        "audit_rights": "حقوق التدقيق",
        "working_hours": "ساعات العمل",
        "non_compete": "عدم المنافسة",
        "ip_assignment": "تخصيص الملكية الفكرية",
        "leave_policy": "سياسة الإجازات",
        "term": "المدة",
        "permitted_use": "الاستخدام المسموح",
        "remedies": "سبل الانتصاف",
        "exceptions": "الاستثناءات",
        "return_or_destroy": "الإرجاع أو الإتلاف",
        "injunctive_relief": "أمر قضائي عاجل",
        "rent": "الإيجار",
        "maintenance": "الصيانة",
        "default": "الإخلال",
        "security_deposit": "التأمين",
        "renewal": "التجديد",
        "insurance": "التأمين",
        "force_majeure": "القوة القاهرة",
        "notice": "الإشعار",
        "compensation": "الأجر/التعويض",
    }
    return arabic_map.get(name, name) if _is_arabic_response(response_language) else name


def _dimension(
    name: str,
    score: int,
    explanation: str,
    evidence: List[Dict[str, str]],
    missing_information: Optional[List[str]] = None,
    recommended_action: Optional[str] = None,
) -> Dict[str, Any]:
    bounded_score = max(0, min(100, score))
    return {
        "name": name,
        "score": bounded_score,
        "explanation": explanation,
        "reason": explanation,
        "evidence": evidence,
        "supporting_evidence": evidence,
        "missing_information": missing_information or [],
        "recommended_action": recommended_action or "Review this area against the cited contract evidence before approval.",
    }


def _normalize_clauses(clauses: Dict[str, str]) -> Dict[str, str]:
    return {str(k).strip().lower(): str(v).strip() for k, v in (clauses or {}).items() if str(v).strip()}


def _find_clause_text(normalized: Dict[str, str], logical_clause: str) -> Tuple[str, str]:
    keywords = CLAUSE_KEYWORDS.get(logical_clause, [logical_clause.replace("_", " ")])
    for key, text in normalized.items():
        key_text = f"{key} {text[:220].lower()}"
        if any(keyword in key_text for keyword in keywords):
            return key, text
    return "", ""


def infer_contract_type_from_clauses(clauses: Dict[str, str]) -> Dict[str, Any]:
    normalized = _normalize_clauses(clauses)
    doc_text = "\n".join([f"{k}\n{v}" for k, v in normalized.items()]).lower()

    scores: Dict[str, int] = {}
    for contract_type, rule in CONTRACT_TYPE_RULES.items():
        score = 0
        for kw in rule["keywords"]:
            if kw in doc_text:
                score += 2
        for req in rule["required"]:
            if _find_clause_text(normalized, req)[1]:
                score += 1
        scores[contract_type] = score

    best_type = max(scores, key=scores.get)
    ordered = sorted(scores.values(), reverse=True)
    gap = (ordered[0] - ordered[1]) if len(ordered) > 1 else ordered[0]
    confidence = min(0.95, 0.45 + max(gap, 0) * 0.08 + ordered[0] * 0.02)

    return {
        "contract_type": best_type,
        "confidence": round(confidence, 2),
        "candidates": scores,
    }


def evaluate_contract_health_from_clauses(clauses: Dict[str, str], response_language: str = "english") -> Dict[str, Any]:
    normalized = _normalize_clauses(clauses)
    contract_type_info = infer_contract_type_from_clauses(clauses)
    contract_type = contract_type_info["contract_type"]
    rules = CONTRACT_TYPE_RULES.get(contract_type, CONTRACT_TYPE_RULES["general_commercial"])

    missing_required: List[str] = []
    missing_recommended: List[str] = []
    ambiguous_clauses: List[Dict[str, str]] = []
    red_flags: List[Dict[str, Any]] = []

    for item in rules["required"]:
        if not _find_clause_text(normalized, item)[1]:
            missing_required.append(item)
    for item in rules["recommended"]:
        if not _find_clause_text(normalized, item)[1]:
            missing_recommended.append(item)

    liability_key, liability_text = _find_clause_text(normalized, "limitation_of_liability")
    term_key, term_text = _find_clause_text(normalized, "termination")
    payment_key, payment_text = _find_clause_text(normalized, "payment_terms")
    law_key, law_text = _find_clause_text(normalized, "governing_law")
    dispute_key, dispute_text = _find_clause_text(normalized, "dispute_resolution")

    risk_score = 88
    risk_evidence: List[Dict[str, str]] = []
    if liability_text:
        risk_evidence.append({"quote": liability_text[:240], "location": f"clause:{liability_key}"})
        if re.search(r"\bunlimited\b|without limitation", liability_text.lower()):
            risk_score -= 55
            red_flags.append({
                "type": "unlimited_liability",
                "severity": "high",
                "evidence": [{"quote": liability_text[:220], "location": f"clause:{liability_key}"}],
            })
    else:
        risk_score -= 35
        red_flags.append({"type": "missing_liability_limit", "severity": "high", "evidence": []})

    if not _find_clause_text(normalized, "indemnification")[1]:
        risk_score -= 12

    comm_score = 90
    comm_evidence: List[Dict[str, str]] = []
    if payment_text:
        comm_evidence.append({"quote": payment_text[:220], "location": f"clause:{payment_key}"})
        if not re.search(r"\b\d+\s*(day|days|month|months)\b", payment_text.lower()):
            comm_score -= 20
            ambiguous_clauses.append({
                "clause": payment_key,
                "reason": _msg("Payment timing is unclear (missing specific due period).", "توقيت الدفع غير واضح (لا توجد مدة استحقاق محددة).", response_language),
            })
    else:
        comm_score -= 35

    if not _find_clause_text(normalized, "scope_of_work")[1]:
        comm_score -= 25
    if not _find_clause_text(normalized, "acceptance_criteria")[1] and contract_type in {"service_agreement", "general_commercial"}:
        comm_score -= 10
        missing_recommended.append("acceptance_criteria")

    comp_score = 86
    comp_evidence: List[Dict[str, str]] = []
    confidentiality_key, confidentiality_text = _find_clause_text(normalized, "confidentiality")
    if confidentiality_text:
        comp_evidence.append({"quote": confidentiality_text[:220], "location": f"clause:{confidentiality_key}"})
    else:
        comp_score -= 20

    if contract_type in {"service_agreement", "general_commercial"} and not _find_clause_text(normalized, "sla")[1]:
        comp_score -= 14
    if not _find_clause_text(normalized, "audit_rights")[1]:
        comp_score -= 8

    term_score = 84
    term_evidence: List[Dict[str, str]] = []
    if term_text:
        term_evidence.append({"quote": term_text[:220], "location": f"clause:{term_key}"})
        if "for cause" in term_text.lower() and "without cause" not in term_text.lower():
            term_score -= 18
            ambiguous_clauses.append({
                "clause": term_key,
                "reason": _msg("Termination appears one-sided (for-cause only).", "بند الإنهاء يبدو أحادي الجانب (لسبب فقط).", response_language),
            })
        if "automatic renewal" in term_text.lower() and "notice" not in term_text.lower():
            term_score -= 18
            red_flags.append({
                "type": "auto_renewal_no_notice",
                "severity": "medium",
                "evidence": [{"quote": term_text[:220], "location": f"clause:{term_key}"}],
            })
    else:
        term_score -= 40

    law_score = 88
    law_evidence: List[Dict[str, str]] = []
    if law_text:
        law_evidence.append({"quote": law_text[:220], "location": f"clause:{law_key}"})
    else:
        law_score -= 35
        red_flags.append({"type": "missing_governing_law", "severity": "high", "evidence": []})

    if dispute_text:
        law_evidence.append({"quote": dispute_text[:220], "location": f"clause:{dispute_key}"})
    else:
        law_score -= 25
        red_flags.append({"type": "missing_dispute_resolution", "severity": "high", "evidence": []})

    dimensions = [
        _dimension("Risk Exposure", risk_score, _msg("Liability cap, indemnity balance, and uncapped exposure.", "حدود المسؤولية وتوازن التعويض والمخاطر غير المحدودة.", response_language), risk_evidence),
        _dimension("Commercial Clarity", comm_score, _msg("Payment certainty, scope detail, and acceptance mechanics.", "وضوح الدفع وتفاصيل نطاق العمل وآلية القبول.", response_language), comm_evidence),
        _dimension("Compliance & Obligations", comp_score, _msg("Operational obligations, confidentiality, SLA/audit governance.", "الالتزامات التشغيلية والسرية وحوكمة مستويات الخدمة والتدقيق.", response_language), comp_evidence),
        _dimension("Term & Renewal Risk", term_score, _msg("Termination rights, renewal control, and notice structure.", "حقوق الإنهاء وضبط التجديد وهيكل الإشعارات.", response_language), term_evidence),
        _dimension("Dispute & Governing Law", law_score, _msg("Jurisdiction clarity and dispute-resolution pathway.", "وضوح الاختصاص القانوني وآلية حل النزاعات.", response_language), law_evidence),
    ]

    health_score = round(sum(d["score"] for d in dimensions) / max(len(dimensions), 1))
    risk_level = "low" if health_score >= 80 else "medium" if health_score >= 60 else "high"

    required_changes: List[str] = []
    if missing_required:
        required_changes.append(
            _msg(f"Add missing mandatory clauses for {contract_type.replace('_', ' ')}: {', '.join(_pretty_clause_name(x, response_language) for x in sorted(set(missing_required)))}.", f"أضف البنود الإلزامية المفقودة لنوع العقد {contract_type.replace('_', ' ')}: {', '.join(_pretty_clause_name(x, response_language) for x in sorted(set(missing_required)))}.", response_language)
        )
    if any(flag["type"] == "unlimited_liability" for flag in red_flags):
        required_changes.append(_msg("Replace uncapped liability with a negotiated cap and narrow carve-outs (fraud/willful misconduct only).", "استبدل المسؤولية غير المحدودة بحد أقصى متفق عليه مع استثناءات ضيقة (الاحتيال/سوء السلوك الجسيم فقط).", response_language))
    if any(flag["type"] in {"missing_governing_law", "missing_dispute_resolution"} for flag in red_flags):
        required_changes.append(_msg("Add explicit governing law and a clear dispute forum (court/arbitration seat and rules).", "أضف قانونًا واجب التطبيق بشكل صريح وحدد جهة فصل النزاع بوضوح (المحكمة/مقر التحكيم والقواعد).", response_language))
    if ambiguous_clauses:
        required_changes.append(_msg("Clarify ambiguous provisions with objective triggers, dates, and measurable obligations.", "وضّح البنود المبهمة عبر معايير موضوعية وتواريخ واضحة والتزامات قابلة للقياس.", response_language))

    approved = health_score >= 70 and not any(flag["severity"] == "high" for flag in red_flags)

    issues = [
        *[f"missing_required:{item}" for item in missing_required],
        *[f"missing_recommended:{item}" for item in sorted(set(missing_recommended))],
        *[flag["type"] for flag in red_flags],
        *[f"ambiguous:{item['clause']}" for item in ambiguous_clauses],
    ]

    return {
        "module": "contract_health",
        "legal_parameters_version": "strict-v2",
        "contract_type": contract_type,
        "contract_type_confidence": contract_type_info["confidence"],
        "contract_type_candidates": contract_type_info["candidates"],
        "approved": approved,
        "health_score": health_score,
        "risk_level": risk_level,
        "reasoning": (
            _msg(f"Detected contract type: {contract_type.replace('_', ' ')}. Health score {health_score}/100 using 5 legal dimensions with type-specific mandatory clause checks.", f"تم تحديد نوع العقد: {contract_type.replace('_', ' ' )}. درجة صحة العقد {health_score}/100 وفق 5 أبعاد قانونية مع تحقق من البنود الإلزامية الخاصة بنوع العقد.", response_language)
        ),
        "missing_critical_clauses": [_pretty_clause_name(x, response_language) for x in sorted(set(missing_required))],
        "missing_recommended_clauses": [_pretty_clause_name(x, response_language) for x in sorted(set(missing_recommended))],
        "ambiguous_clauses": ambiguous_clauses,
        "issues": issues,
        "required_changes": required_changes,
        "dimensions": dimensions,
        "red_flags": red_flags,
        "evidence": [e for d in dimensions for e in d.get("evidence", [])][:8],
    }
