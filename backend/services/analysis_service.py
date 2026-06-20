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


def _human_clause_fields(clause_type: str, status: str, details: dict[str, Any], evidence: list[dict[str, Any]], language: str = "en") -> dict[str, str]:
    has_evidence = bool(evidence)
    detail_bits = []
    for label, key in [("amounts", "monetary_amounts"), ("timing", "payment_timing"), ("dates", "dates"), ("durations", "durations"), ("notice", "notice_periods")]:
        if details.get(key):
            detail_bits.append(f"{label}: {', '.join(details[key][:3])}")
    detail_sentence = f" Key extracted details include {('; '.join(detail_bits))}." if detail_bits else ""
    label = clause_type.replace("_", " ")
    if language == "ar":
        ar_label = label
        ar_details = f" التفاصيل المستخرجة تشمل: {('؛ '.join(detail_bits))}." if detail_bits else ""
        if status == "missing":
            return {
                "simple_explanation": f"لم يظهر في النص بند واضح بخصوص {ar_label}.",
                "why_it_matters": f"هذا مهم لأن بند {ar_label} يساعد الأطراف على فهم الحقوق والالتزامات والتوقيت والمسؤوليات قبل الاعتماد على العقد.",
                "risk_in_plain_english": f"الخطر ببساطة أن غياب أو غموض بند {ar_label} قد يؤدي إلى خلاف لاحق حول الحقوق أو الالتزامات أو التعويضات.",
                "what_to_check_next": f"تأكد مع المسؤول التجاري أو القانوني مما إذا كان يجب إضافة بند واضح ومناسب عن {ar_label} في هذه الصفقة.",
                "negotiation_note": f"ناقش صياغة محددة وواضحة لبند {ar_label} إذا كان هذا الموضوع مهمًا لأي طرف.",
                "completeness": "مفقود",
            }
        return {
            "simple_explanation": f"هذا البند يتناول {ar_label} في العقد.{ar_details}",
            "why_it_matters": f"هذا مهم لأنه يوضح كيف يعمل موضوع {ar_label} عمليًا، ومن المسؤول عن ماذا.",
            "risk_in_plain_english": "الخطر ببساطة أن بعض التفاصيل المهمة قد تكون ناقصة أو غير متوازنة أو غير واضحة إذا لم تظهر صراحة في الدليل المستخرج.",
            "what_to_check_next": "تأكد من التفاصيل المستخرجة، خطوات الموافقة، المواعيد النهائية، الاستثناءات، والعواقب مع المسؤول التجاري أو القانوني.",
            "negotiation_note": "إذا كان البند يؤثر على المال أو التوقيت أو الملكية أو الإنهاء أو القيود، فناقش حدودًا ومسؤوليات واستثناءات أوضح.",
            "completeness": "قوي" if has_evidence and len(details) >= 3 else "جزئي",
        }
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




def _ar(text: str, language: str) -> str:
    if language != "ar":
        return text
    translations = {
        "This clause appears to address": "هذا البند يتناول",
        "The review did not find clear contract text for": "لم يجد التحليل نصًا واضحًا بخصوص",
        "Confirm the extracted details": "تأكد من التفاصيل المستخرجة",
        "The main risk is": "الخطر الأساسي هو",
    }
    for en, ar in translations.items():
        text = text.replace(en, ar)
    return text


def _missing_detail_questions(clause_type: str, details: dict[str, Any]) -> list[str]:
    questions = []
    if clause_type == "termination":
        if not details.get("notice_periods"):
            questions.append("Does the termination clause include a notice period?")
        questions.append("Does it explain termination for cause, cure periods, resignation rights, final payment, and surviving obligations?")
    elif clause_type == "payment":
        if not details.get("monetary_amounts"):
            questions.append("Is the amount or salary clearly stated?")
        questions.append("Are deductions, taxes, late payment, final settlement, and payment disputes clearly defined?")
    elif clause_type == "intellectual_property":
        questions.append("Does the IP clause exclude pre-existing personal work and side projects?")
    elif clause_type == "confidentiality":
        questions.append("Does the confidentiality clause define exclusions, duration, permitted disclosures, and return/destruction duties?")
    elif clause_type == "dispute_resolution":
        questions.append("Is the dispute process clear enough if a disagreement happens?")
    else:
        questions.append("Are scope, responsibilities, timing, exceptions, and consequences clear enough for business use?")
    return questions[:3]




def _arabic_questions_for_clause(ctype: str) -> list[str]:
    ctype = (ctype or "").lower()
    templates = {
        "termination": [
            "هل يوضح العقد مدة الإشعار المطلوبة قبل الإنهاء؟",
            "هل يوضح العقد حقوق الإنهاء لكل طرف؟",
            "هل يوضح العقد ما يحدث للدفعات والالتزامات بعد الإنهاء؟",
        ],
        "payment": [
            "هل يوضح العقد مبلغ الدفع وموعده وطريقة السداد؟",
            "هل يوضح العقد الخصومات أو الضرائب أو التسوية النهائية؟",
            "هل يوضح العقد ما يحدث عند تأخر الدفع أو وجود نزاع على المبلغ؟",
        ],
        "confidentiality": [
            "ما نوع المعلومات السرية المشمولة بالحماية؟",
            "كم تستمر التزامات السرية بعد انتهاء العقد؟",
            "هل توجد استثناءات واضحة على الالتزام بالسرية؟",
        ],
        "intellectual_property": [
            "هل يوضح العقد من يملك الأعمال أو البرمجيات أو التصاميم الناتجة؟",
            "هل يستثني العقد الأعمال السابقة أو المشاريع الشخصية؟",
            "هل يوضح حقوق الاستخدام أو التسليم أو الترخيص؟",
        ],
        "non_compete": [
            "هل مدة ونطاق عدم المنافسة واضحان ومعقولان؟",
            "هل يحدد العقد المنطقة الجغرافية أو نوع الأعمال المحظورة؟",
            "هل يحتاج هذا القيد إلى مراجعة قانونية حسب الاختصاص القضائي؟",
        ],
        "non_solicitation": [
            "هل يوضح العقد من لا يجوز استقطابه أو التواصل معه؟",
            "هل مدة القيد ونطاقه واضحان؟",
            "هل القيد متوازن وقابل للمراجعة القانونية؟",
        ],
        "liability": [
            "هل يوضح العقد حدود المسؤولية بين الأطراف؟",
            "هل توجد استثناءات أو تعويضات واضحة؟",
            "هل يوضح العقد الإجراء عند حدوث مطالبة أو ضرر؟",
        ],
        "governing_law": [
            "هل يوضح العقد القانون المطبق؟",
            "هل يحدد جهة الفصل في النزاعات؟",
            "هل آلية حل النزاع واضحة بما يكفي؟",
        ],
        "dispute_resolution": [
            "هل يوضح العقد خطوات حل النزاع؟",
            "هل يوجد تصعيد واضح قبل المحكمة أو التحكيم؟",
            "هل يحدد العقد الجهة أو الآلية المعتمدة لحل الخلاف؟",
        ],
    }
    return templates.get(ctype, [
        "ما الالتزامات الأساسية التي يفرضها هذا البند؟",
        "ما التفاصيل التي يجب تأكيدها قبل التوقيع؟",
        "هل توجد شروط أو استثناءات أو مخاطر غير واضحة؟",
    ])


def _questions_for_clause(ctype: str, lang: str = "en") -> list[str]:
    if lang == "ar":
        return _arabic_questions_for_clause(ctype)
    return _missing_detail_questions(ctype, {})

def _arabic_action_for_clause(clause_type: str) -> str:
    templates = {
        "termination": "مراجعة بند الإنهاء: قبل التوقيع، تأكد من وجود مدة إشعار واضحة، وحقوق الإنهاء لكل طرف، والتسوية النهائية، والالتزامات التي تستمر بعد انتهاء العقد.",
        "payment": "مراجعة بند الدفع: تأكد من قيمة المبلغ، موعد الدفع، طريقة الدفع، الخصومات، الضرائب، وآلية التعامل مع التأخير أو النزاع على المدفوعات.",
        "liability": "مراجعة بند المسؤولية: وضّح حدود المسؤولية، الاستثناءات، التعويضات، والإجراءات المتبعة عند حدوث ضرر أو مطالبة.",
        "intellectual_property": "مراجعة بند الملكية الفكرية: تأكد من تحديد ملكية الأعمال، واستثناء الأعمال السابقة أو المشاريع الشخصية، وحقوق استخدام البرمجيات أو التصاميم.",
        "confidentiality": "مراجعة بند السرية: تأكد من نطاق المعلومات السرية، مدة الالتزام، الاستثناءات، وما يجب فعله بالمعلومات بعد انتهاء العقد.",
        "non_compete": "مراجعة القيود التنافسية وعدم الاستقطاب: تأكد من أن المدة، النطاق الجغرافي، والأطراف المشمولة واضحة ومعقولة وقابلة للمراجعة القانونية.",
        "dispute_resolution": "مراجعة بند حل النزاعات: تأكد من وجود خطوات تصعيد واضحة، وجهة مختصة، وإجراءات عملية عند حدوث خلاف.",
        "governing_law": "مراجعة بند القانون الحاكم: تأكد من تحديد القانون والجهة المختصة بطريقة واضحة ومناسبة للأطراف.",
    }
    return templates.get(clause_type, "مراجعة هذا البند: تأكد من وضوح المسؤوليات، التوقيت، الاستثناءات، والعواقب قبل الاعتماد على العقد.")

def _clause_decision(clause: dict[str, Any], language: str = "en") -> dict[str, Any]:
    ctype = clause["type"]
    status = clause["status"]
    details = clause.get("extracted_details", {})
    critical = ctype in CRITICAL
    if status == "missing":
        decision, risk, priority = "Missing", "High" if critical else "Medium", "High" if critical else "Medium"
        why = f"No direct evidence was found for the {ctype.replace('_', ' ')} clause."
        fix = f"Add clear {ctype.replace('_', ' ')} language if this topic matters to the transaction."
    elif ctype == "termination" and not details.get("notice_periods"):
        decision, risk, priority = "Needs clarification", "Medium", "High"
        why = "The clause was found, but the extracted evidence does not clearly show notice period, termination rights, cure period, final settlement, or survival obligations."
        fix = "Before signing, confirm notice period, termination for cause, employee resignation rights, final payment, and post-termination obligations."
    elif ctype == "payment" and (not details.get("monetary_amounts") or not details.get("payment_timing")):
        decision, risk, priority = "Needs strengthening", "Medium", "High"
        why = "Payment-related language was found, but the extracted evidence does not show all key payment mechanics."
        fix = "Confirm amount, payment timing, method, deductions, taxes, late payment handling, final settlement, and dispute process."
    elif ctype == "intellectual_property" and clause.get("found"):
        decision, risk, priority = "Needs legal review", "Medium", "High"
        why = "IP language can affect ownership of work product, pre-existing work, side projects, and inventions created outside work."
        fix = "Clarify exclusions for pre-existing work, personal projects, licenses, and work created outside the role."
    elif status == "partial" or len(details) < 2:
        decision, risk, priority = "Needs clarification", "Medium", "Medium"
        why = "The clause appears to exist, but the extracted evidence does not show enough detail to rely on it without review."
        fix = "Clarify responsibilities, timing, exceptions, approval steps, consequences, and owner accountability."
    else:
        decision, risk, priority = "Acceptable", "Low", "Low"
        why = "The clause has direct evidence and enough extracted detail for business review, subject to final human review."
        fix = "Confirm the extracted terms match the original document and the business intent."
    business_impact = "This decision support highlights whether the clause is ready for business review, needs revision, or needs legal attention before signature."
    if language == "ar":
        ar_map = {"Acceptable": "مقبول للمراجعة التجارية", "Needs strengthening": "يحتاج إلى تقوية", "Needs clarification": "يحتاج إلى توضيح", "Missing": "مفقود", "High risk": "خطر مرتفع", "Needs legal review": "يحتاج إلى مراجعة قانونية"}
        decision = ar_map.get(decision, decision)
        risk_map = {"Low": "منخفض", "Medium": "متوسط", "High": "مرتفع"}
        risk = risk_map.get(risk, risk)
        priority = risk_map.get(priority, priority)
        why = "يعتمد هذا القرار على الأدلة المستخرجة والتفاصيل الناقصة في هذا البند. يجب مراجعة ما يظهر في الدليل وما لا يظهر قبل الاعتماد عليه."
        fix = _arabic_action_for_clause(ctype)
        business_impact = "هذا القرار يساعد المستخدم على معرفة ما إذا كان البند مقبولًا للمراجعة التجارية أو يحتاج إلى تعديل أو مراجعة قانونية."
        questions = _questions_for_clause(ctype, "ar")
    else:
        questions = _missing_detail_questions(ctype, details)
    return {"clause_decision": decision, "business_impact": business_impact, "risk_level": risk, "why_this_decision": why, "recommended_fix": fix, "questions_to_ask": questions, "priority": priority}


def _overall_decision(rule_result: dict[str, Any], clauses: list[dict[str, Any]], language: str = "en") -> dict[str, Any]:
    must_fix = []
    should_review = []
    acceptable = []
    for clause in clauses:
        decision = str(clause.get("clause_decision", ""))
        title = clause.get("title", clause.get("type", "Clause"))
        if "Missing" in decision or "High risk" in decision:
            must_fix.append(f"Fix or add {title} before signing.")
        elif "Needs" in decision or "يحتاج" in decision:
            should_review.append(f"Review {title}: {clause.get('recommended_fix')}")
        else:
            acceptable.append(f"{title} appears acceptable for business review based on current evidence.")
    score = rule_result.get("health_score", 0)
    if must_fix or score < 55:
        review_decision = "High risk - do not sign yet" if len(must_fix) >= 2 else "Needs legal review"
        confidence = "High" if must_fix else "Medium"
    elif should_review or score < 80:
        review_decision = "Needs revision"
        confidence = "Medium"
    else:
        review_decision = "Ready for business review"
        confidence = "Medium"
    reasoning = "Decision is based on missing critical clauses, extracted detail completeness, evidence quality, and clause-level risk signals. This is decision support, not final legal advice."
    if language == "ar":
        decision_map = {"Ready for business review": "جاهز للمراجعة التجارية", "Needs revision": "يحتاج إلى تعديل", "Needs legal review": "يحتاج إلى مراجعة قانونية", "High risk - do not sign yet": "خطر مرتفع - لا توقّع الآن"}
        review_decision = decision_map.get(review_decision, review_decision)
        confidence = {"High": "عالية", "Medium": "متوسطة", "Low": "منخفضة"}.get(confidence, confidence)
        reasoning = "يعتمد القرار على البنود الناقصة، اكتمال التفاصيل المستخرجة، جودة الأدلة، وإشارات المخاطر لكل بند. هذا دعم لاتخاذ القرار وليس رأيًا قانونيًا نهائيًا."
        must_fix = [item.replace("Fix or add ", "أصلح أو أضف بند ").replace(" before signing.", " قبل التوقيع.") for item in must_fix]
        should_review = [str(item).replace("Review ", "مراجعة بند ") for item in should_review]
        acceptable = [str(item).replace(" appears acceptable for business review based on current evidence.", " يبدو مقبولًا للمراجعة التجارية بناءً على الأدلة الحالية.") for item in acceptable]
    return {"review_decision": review_decision, "decision_confidence": confidence, "decision_reasoning": reasoning, "top_decision_drivers": must_fix[:2] + should_review[:3], "must_fix_before_signing": must_fix, "should_review": should_review, "acceptable_points": acceptable[:5], "human_review_required": bool(must_fix or should_review)}


def _action_plan(decision: dict[str, Any], clauses: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    def action_item(action: str, clause: str, priority: str, reason: str, owner: str) -> dict[str, str]:
        return {"action": action, "related_clause": clause, "priority": priority, "reason": reason, "evidence_basis": "Extracted clause evidence and missing detail analysis", "owner_suggestion": owner}
    must = []
    should = []
    confirm = []
    for clause in clauses:
        title = clause.get("title", "Clause")
        item = action_item(clause.get("recommended_fix", "Clarify this clause."), title, clause.get("priority", "Medium"), clause.get("why_this_decision", "Decision support signal."), "Legal" if clause.get("priority") == "High" else "Business Owner")
        dec = str(clause.get("clause_decision", ""))
        if "Missing" in dec or "High" in str(clause.get("risk_level")) or "مرتفع" in str(clause.get("risk_level")):
            must.append(item)
        elif "Needs" in dec or "يحتاج" in dec:
            should.append(item)
        else:
            confirm.append(item)
    return {"must_fix_before_signing": must[:5], "should_clarify": should[:6], "good_to_confirm": confirm[:6], "optional_improvements": []}

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


def _rule_based_analysis(text: str, explanation_language: str = "en") -> dict[str, Any]:
    clauses = []
    for key, terms in CLAUSE_PATTERNS.items():
        evidence = _evidence_for(text, terms)
        evidence_text = evidence[0]["text"] if evidence else ""
        details = _details_from_evidence(key, evidence_text)
        status = "found" if evidence and len(details) >= 2 else "partial" if evidence else "missing" if key in CRITICAL else "partial"
        human = _human_clause_fields(key, status, details, evidence, explanation_language)
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


def _fallback_ai_fields(rule_result: dict[str, Any], status: str, parse_failed: bool = False, error: str | None = None, explanation_language: str = "en") -> dict[str, Any]:
    missing = rule_result["missing_critical_clauses"]
    clauses = []
    for clause in rule_result["clauses"]:
        human = _human_clause_fields(clause["type"], clause["status"], clause.get("extracted_details", {}), clause.get("evidence", []), explanation_language)
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
        "ai_overall_assessment": "Rule-based decision support is shown using extracted clause evidence, missing-clause signals, and health scoring because the LLM path was unavailable or could not be parsed.",
        "key_strengths": [c["title"] for c in rule_result["clauses"] if c["found"]][:5],
        "key_risks": [r["title"] for r in rule_result["risks"]],
        "missing_clauses": missing,
        "recommended_actions": [r["suggested_mitigation"] for r in rule_result["risks"]] or ["Review the extracted key terms, confirm business assumptions, and complete human legal review before signature."],
        "key_terms": rule_result.get("key_terms", []),
        "clauses": clauses,
        "raw_llm_response": {},
    }


def _ai_prompt(text: str, rule_result: dict[str, Any], explanation_language: str = "en") -> str:
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

EXPLANATION_LANGUAGE: {explanation_language}
If explanation_language is ar, write layman explanations, practical notes, recommendations, and negotiation notes in clear simple Arabic. Do not translate names, amounts, dates, model names, URLs, or quoted evidence unnecessarily.

CONTRACT_TEXT:
{contract_excerpt}
"""


def _merge_ai(rule_result: dict[str, Any], ai_output: dict[str, Any], explanation_language: str = "en") -> dict[str, Any]:
    ai_clause_by_type = {str(item.get("type", "")).lower(): item for item in ai_output.get("clauses", []) if isinstance(item, dict)}
    clauses = []
    for clause in rule_result["clauses"]:
        ai_clause = ai_clause_by_type.get(clause["type"], {})
        human = _human_clause_fields(clause["type"], clause["status"], clause.get("extracted_details", {}), clause.get("evidence", []), explanation_language)
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


def analyze_text(text: str, explanation_language: str = "en", ui_language: str = "en") -> dict[str, Any]:
    settings = get_settings()
    text = (text or "").strip()
    rule_result = _rule_based_analysis(text, explanation_language)
    health = llm_health()
    llm_debug = {"health": health, "model": settings.ollama_model, "ollama_url": settings.ollama_base_url}
    if not health.get("reachable"):
        ai_fields = _fallback_ai_fields(rule_result, "LLM unavailable", error=health.get("error"), explanation_language=explanation_language)
    else:
        try:
            retry = _ai_prompt(text, rule_result, explanation_language) + "\nReturn valid JSON only. No markdown. No prose outside JSON."
            raw_ai = generate_structured_json(_ai_prompt(text, rule_result, explanation_language), retry_prompt=retry)
            merged = _merge_ai(rule_result, raw_ai, explanation_language)
            ai_fields = {
                "source": "hybrid",
                "llm_used": True,
                "degraded_mode": False,
                "ai_status": "LLM analysis completed",
                "llm_parse_failed": False,
                "llm_error": None,
                "executive_summary": raw_ai.get("executive_summary") or "AI review completed, but no executive summary was returned.",
                "ai_overall_assessment": raw_ai.get("ai_overall_assessment") or "AI-assisted decision support is based on extracted evidence, missing details, and clause-level risk signals.",
                "key_strengths": raw_ai.get("key_strengths") or [],
                "key_risks": raw_ai.get("key_risks") or [],
                "missing_clauses": raw_ai.get("missing_clauses") or rule_result["missing_critical_clauses"],
                "recommended_actions": raw_ai.get("recommended_actions") or [],
                "key_terms": raw_ai.get("key_terms") or rule_result.get("key_terms", []),
                "review_decision": raw_ai.get("review_decision"),
                "priority_action_plan": raw_ai.get("priority_action_plan"),
                "follow_up_questions": raw_ai.get("follow_up_questions"),
                "clauses": merged["clauses"],
                "raw_llm_response": raw_ai,
            }
        except Exception as exc:
            llm_debug["parse_or_generation_error"] = str(exc)
            ai_fields = _fallback_ai_fields(rule_result, "LLM response could not be parsed", parse_failed=True, error=str(exc), explanation_language=explanation_language)
    for clause in ai_fields["clauses"]:
        decision_fields = _clause_decision(clause, explanation_language)
        clause.update(decision_fields)
    review_decision = ai_fields.get("review_decision") or _overall_decision(rule_result, ai_fields["clauses"], explanation_language)
    action_plan = ai_fields.get("priority_action_plan") or _action_plan(review_decision, ai_fields["clauses"])
    follow_up_questions = ai_fields.get("follow_up_questions") or [
        "Does the termination clause include a notice period?",
        "Are salary deductions and final settlement clearly defined?",
        "Does the IP clause exclude pre-existing personal work?",
        "Are non-compete restrictions reasonable in scope and duration?",
        "Is the dispute process clear enough if a disagreement happens?",
    ]
    evidence_trace = []
    for clause in ai_fields["clauses"]:
        if clause.get("evidence"):
            for item in clause["evidence"]:
                evidence_trace.append({"clause": clause["title"], "text": item.get("text"), "source": item.get("source", "extracted_text"), "keyword": item.get("keyword"), "confidence": clause.get("confidence")})
        else:
            evidence_trace.append({"clause": clause["title"], "text": "No direct evidence captured for this clause.", "source": "rule-based absence", "keyword": None, "confidence": clause.get("confidence")})
    return {
        "schema_version": "hybrid-analysis-v1",
        "explanation_language": explanation_language,
        "ui_language": ui_language,
        "review_decision": review_decision,
        "priority_action_plan": action_plan,
        "follow_up_questions": follow_up_questions,
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


async def analyze_contract_record(db, contract: dict, explanation_language: str = "en", ui_language: str = "en"):
    analysis = analyze_text(contract.get("extracted_text", ""), explanation_language=explanation_language, ui_language=ui_language)
    doc = {"owner_user_id": contract["owner_user_id"], "contract_id": str(contract["_id"]), "analysis": analysis, "created_at": datetime.now(timezone.utc)}
    result = await db.analyses.insert_one(doc)
    doc["_id"] = result.inserted_id
    await db.contracts.update_one({"_id": contract["_id"]}, {"$set": {"latest_analysis_id": str(result.inserted_id), "analysis_summary": analysis, "updated_at": datetime.now(timezone.utc)}})
    return analysis
