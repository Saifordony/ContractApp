from datetime import datetime, timezone
import asyncio
import re
from typing import Any

from backend.services.analysis_service import parse_contract_sections, retrieve_evidence as hybrid_retrieve_evidence
from backend.services.llm_service import generate_structured_json, llm_health
from backend.config import get_settings
from backend.schemas.ai import ChatAnswer

CONTRACT_KEYWORDS = {"clause", "payment", "leave", "termination", "risk", "rights", "obligations", "liability", "confidential", "salary", "fee", "renewal", "governing", "negotiate", "contract", "agreement", "can i", "what does this mean", "summarize", "rewrite"}
SMALL_TALK = {"hi", "hello", "hey", "thanks", "thank you", "who are you"}
APP_HELP = {"how do i upload", "how do i analyze", "how does this app", "help", "what can you do"}
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
ARABIC_CONTRACT_CONCEPTS: dict[str, list[str]] = {
    "leave": ["اجازة", "عطلة", "سنوية", "غياب"],
    "payment": ["راتب", "اجر", "تعويض", "دفعة", "دفع", "مبلغ", "مكافاة"],
    "termination": ["انهاء", "فسخ", "استقالة", "ينتهي", "انتهاء"],
    "confidentiality": ["سرية", "معلومات سرية"],
    "intellectual_property": ["ملكية فكرية", "كود", "برمجيات", "تصميم", "الشغل", "العمل"],
    "non_compete": ["عدم منافسة", "منافسة", "عدم استقطاب", "استقطاب"],
    "liability": ["مسؤولية", "تعويض", "ضرر", "اضرار"],
    "dispute_resolution": ["قانون", "نزاع", "محكمة", "تحكيم", "خلاف"],
    "probation": ["فترة تجربة", "تجربة"],
    "working_hours": ["ساعات العمل", "دوام"],
    "risk": ["مخاطر", "خطر", "وش المخاطر", "ما المخاطر"],
    "negotiation": ["اتفاوض", "تفاوض", "وش لازم اتفاوض", "تفاوض عليه"],
    "clause": ["بند", "شرط", "العقد"],
}
CONCEPT_SEARCH_TERMS: dict[str, list[str]] = {
    "leave": ["leave", "annual leave", "vacation", "paid leave", "holiday", "absence"],
    "payment": ["salary", "payment", "compensation", "wage", "monthly", "amount", "bank transfer"],
    "termination": ["termination", "resignation", "notice period", "end of employment", "final settlement"],
    "confidentiality": ["confidential", "confidentiality", "non-disclosure", "proprietary information"],
    "intellectual_property": ["intellectual property", "work product", "software", "code", "designs", "inventions"],
    "non_compete": ["non-compete", "non compete", "non-solicitation", "restrictive covenant"],
    "liability": ["liability", "indemnity", "damages", "compensation", "claim"],
    "dispute_resolution": ["governing law", "dispute", "court", "arbitration", "jurisdiction"],
    "probation": ["probation", "trial period"],
    "working_hours": ["working hours", "hours of work", "work schedule"],
}


def contains_arabic(text: str) -> bool:
    return bool(ARABIC_RE.search(text or ""))


def normalize_arabic_query(question: str) -> str:
    q = ARABIC_DIACRITICS_RE.sub("", question or "")
    q = q.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي"}))
    q = re.sub(r"[؟?،,؛;:!()\[\]{}\"']", " ", q)
    q = re.sub(r"\s+", " ", q)
    return q.strip().lower()


def concepts_for_question(question: str) -> list[str]:
    normalized = normalize_arabic_query(question)
    lower = (question or "").lower()
    concepts: list[str] = []
    for concept, arabic_terms in ARABIC_CONTRACT_CONCEPTS.items():
        if any(normalize_arabic_query(term) in normalized for term in arabic_terms):
            concepts.append(concept)
    for concept, english_terms in CONCEPT_SEARCH_TERMS.items():
        if any(term in lower for term in english_terms):
            concepts.append(concept)
    return list(dict.fromkeys(concepts))


def _chat_language(question: str, explanation_language: str = "en") -> str:
    return "ar" if contains_arabic(question) else explanation_language


def classify_question(question: str) -> str:
    q = (question or "").lower().strip()
    normalized_ar = normalize_arabic_query(question)
    if any(term in q for term in APP_HELP):
        return "app_help"
    if normalized_ar in {"مرحبا", "اهلا", "هلا", "السلام عليكم", "شكرا"}:
        return "small_talk"
    if q in SMALL_TALK or any(q.startswith(term) for term in SMALL_TALK):
        return "small_talk"
    arabic_concepts = concepts_for_question(question)
    if any(term in normalized_ar for term in ["ما معني", "وش معني", "ايش معني", "يعني ايه"]) and not any(term in normalized_ar for term in ["بند", "العقد", "عقدي"]):
        return "general_contract_concept"
    if arabic_concepts:
        return "contract_specific"
    if any(term in q for term in CONTRACT_KEYWORDS):
        return "contract_specific"
    if any(term in q for term in ["what is", "explain", "define", "meaning of"]):
        return "general_contract_concept"
    return "unrelated_general"


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]


def retrieve_evidence(contract_text: str, question: str, limit: int = 4, contract_id: str = "chat") -> list[dict[str, Any]]:
    chunks = parse_contract_sections(contract_text)
    concepts = concepts_for_question(question)
    clause_type = concepts[0] if concepts else None
    query = question
    for concept in concepts:
        query += " " + " ".join(CONCEPT_SEARCH_TERMS.get(concept, []))
    evidence = hybrid_retrieve_evidence(contract_id, query, chunks, top_k=limit, clause_type=clause_type)
    for item in evidence:
        item.setdefault("clause", item.get("section_title") or "Relevant contract text")
        item.setdefault("location", item.get("section_title") or "Extracted contract text")
        item.setdefault("source", "simple_lexical_retrieval")
    return evidence


def _confidence(evidence: list[dict[str, Any]], answer_type: str) -> float:
    if answer_type not in {"contract_specific", "general_contract_concept"}:
        return 0.7
    if len(evidence) >= 2:
        return 0.86
    if evidence:
        return 0.62
    return 0.25


def _confidence_note(confidence: float) -> str:
    if confidence >= 0.8:
        return "High — the contract clearly mentions this."
    if confidence >= 0.5:
        return "Medium — the contract partly answers this, but some details should be confirmed."
    return "Low — the contract does not clearly answer this."


def _confidence_note_ar(confidence: float) -> str:
    if confidence >= 0.8:
        return "الثقة: عالية — العقد يذكر هذه النقطة بوضوح."
    if confidence >= 0.5:
        return "الثقة: متوسطة — العقد يجيب جزئيًا، لكن بعض التفاصيل تحتاج إلى تأكيد."
    return "الثقة: منخفضة — العقد لا يجيب عن هذه النقطة بوضوح."


def _follow_ups_for_question(question: str, language: str) -> list[str]:
    concepts = concepts_for_question(question)
    if language == "ar":
        if "leave" in concepts:
            return ["هل يستطيع صاحب العمل رفض الإجازة؟", "ما النص الخاص بالإجازة في العقد؟", "هل يوجد إجازة خاصة للزواج أو شهر العسل؟", "ماذا أسأل الموارد البشرية قبل تقديم الطلب؟"]
        if "payment" in concepts:
            return ["متى يتم دفع الراتب؟", "هل يوضح العقد الخصومات أو التسوية النهائية؟", "ماذا أسأل قسم المالية قبل التوقيع؟"]
        if "termination" in concepts:
            return ["هل توجد مدة إشعار واضحة؟", "هل أقدر أستقيل حسب العقد؟", "ما الالتزامات بعد انتهاء العقد؟"]
        return ["اعرض النص الدقيق في العقد", "ما المخاطر التي يجب الانتباه لها؟", "ماذا يجب أن أتأكد منه قبل التوقيع؟"]
    if "leave" in concepts:
        return ["Can the employer reject my leave request?", "Show me the exact leave clause", "Is special leave mentioned?", "What should I ask HR before requesting leave?"]
    return ["Show me the exact clause", "What does this mean in simple terms?", "Is this risky?", "What should I ask before signing?"]


def _general_answer(question: str, answer_type: str, explanation_language: str = "en") -> dict[str, Any]:
    q = (question or "").strip()
    language = _chat_language(question, explanation_language)
    if answer_type == "small_talk":
        answer = "أهلًا — أقدر أساعدك في فهم العقد المحدد، شرح البنود ببساطة، وتحديد المخاطر أو نقاط التفاوض." if language == "ar" else "Hi — I can help you review the selected contract, explain clauses in plain English, identify risks, or answer general follow-up questions."
        summary = "يمكنك السؤال عن الالتزامات، الإجازة، الدفع، الإنهاء، المخاطر، أو نقاط التفاوض." if language == "ar" else "You can ask about obligations, leave, payment, termination, risk, or negotiation points."
    elif answer_type == "app_help":
        answer = "استخدم صفحة العقود لرفع المستند، ثم افتح تحليل العقد للمراجعة المنظمة أو محادثة العقد لطرح أسئلة عن العقد المحدد." if language == "ar" else "Use the Contracts page to upload a document, then open Contract Analysis for a structured review or Contract Chat to ask questions about the selected contract."
        summary = "يجمع التطبيق بين استخراج الأدلة بالقواعد وشرح مدعوم بالذكاء الاصطناعي عند توفر النموذج." if language == "ar" else "The app combines rule-based evidence extraction with AI-assisted explanations when the model is available."
    else:
        answer = f"هذا شرح عام لسؤالك: {q}. إذا أردت، أستطيع أيضًا مقارنته بالعقد المحدد." if language == "ar" else f"Here is a general explanation: {q} is a concept I can discuss generally. If you want, I can also compare it to the selected contract."
        summary = "هذه إجابة عامة وليست مبنية على العقد المحدد إلا إذا طلبت المقارنة معه." if language == "ar" else "This answer is general and not based on the selected contract unless you ask me to compare it."
    if language == "ar":
        practical_note = "إذا كان سؤالك عن العقد المحدد، اذكر الموضوع أو اسم البند المطلوب."
    else:
        practical_note = "If your question is about the selected contract, ask it with the relevant topic or clause name."
    follow_ups = ["لخص هذا العقد", "ما أهم المخاطر؟", "اشرح الالتزامات الأساسية", "ما الذي يجب أن أتفاوض عليه؟"] if language == "ar" else ["Summarize this contract", "What risks should I review first?", "Explain the key obligations", "What should I negotiate?"]
    return {"answer": answer, "answer_type": answer_type, "confidence": 0.7, "confidence_label": _confidence_note_ar(0.7) if language == "ar" else _confidence_note(0.7), "used_contract": False, "evidence": [], "plain_english_summary": summary, "practical_note": practical_note, "follow_up_suggestions": follow_ups, "degraded_mode": False, "llm_used": False, "explanation_language": explanation_language, "response_language": language}


def _fallback_contract_answer(question: str, evidence: list[dict[str, Any]], answer_type: str, llm_unavailable: bool = False, explanation_language: str = "en") -> dict[str, Any]:
    confidence = _confidence(evidence, answer_type)
    language = _chat_language(question, explanation_language)
    concepts = concepts_for_question(question)
    if evidence:
        evidence_text = evidence[0]["text"]
        answer = f"The contract appears to address this. In simple terms, the relevant text says: {evidence_text}"
        practical = "Review the quoted clause, confirm any approval steps or conditions, and ask the relevant business owner or counsel if the wording is unclear."
    else:
        answer = "I could not find contract evidence that clearly answers this question. The contract text provided does not show enough evidence to confirm this point."
        practical = "Ask for clarification or have the missing point added to the contract if it matters to the deal."
    if language == "ar":
        if evidence:
            answer = f"ينص العقد على النص التالي المتعلق بسؤالك: {evidence[0]['text']} لا أستطيع تأكيد حق أو موافقة غير مذكورة صراحة في هذا النص، لذلك اعتبر الإجابة مقيدة بما ورد في الدليل فقط."
            practical = "راجع النص المقتبس، وتأكد من الشروط أو الموافقات أو الرصيد أو المواعيد غير الظاهرة في الدليل مع صاحب العلاقة أو المستشار القانوني."
            summary = "هذه إجابة مرتبطة بالعقد ومبنية على النص المستخرج."
        else:
            answer = "لم أجد دليلًا واضحًا في العقد يجيب عن هذا السؤال. النص المتاح لا يكفي لتأكيد هذه النقطة."
            practical = "اطلب توضيحًا أو أضف هذه النقطة إلى العقد إذا كانت مهمة للصفقة."
            summary = "لم يتم العثور على دليل كافٍ في العقد المحدد."
    else:
        summary = answer
    if llm_unavailable:
        answer = ("نموذج الذكاء الاصطناعي غير متاح — تم عرض إجابة مبنية على القواعد. " if language == "ar" else "AI model unavailable — rule-based contract answer shown. ") + answer
    return _validate_chat_answer({"answer": answer, "short_answer": summary, "answer_type": answer_type, "intent": answer_type, "confidence": confidence, "confidence_label": _confidence_note_ar(confidence) if language == "ar" else _confidence_note(confidence), "used_contract": True, "evidence": evidence, "missing_information": [] if evidence else ["Contract evidence did not clearly answer the question."], "risk_note": "AI-assisted review only; not final legal advice.", "suggested_next_step": practical, "plain_english_summary": summary, "practical_note": practical, "follow_up_suggestions": _follow_ups_for_question(question, language), "degraded_mode": llm_unavailable, "llm_used": False, "model_used": None, "explanation_language": explanation_language, "response_language": language, "language": language, "is_legal_advice_disclaimer": True})


def _chat_prompt(question: str, contract_text: str, evidence: list[dict[str, Any]], answer_type: str, explanation_language: str = "en") -> str:
    return f"""
You are a helpful contract intelligence assistant. Speak naturally like ChatGPT. You can answer normal questions, small talk, and app questions. When the user asks about the selected contract, use only the contract text and extracted evidence. Do not invent contract facts. If the contract does not answer, say so clearly. Explain in simple language. Do not provide final legal advice. Give practical business-friendly next steps.
When the user writes in Arabic, answer in clear natural Arabic. If the question is about the selected contract, use contract evidence even if the contract is written in English. Translate the meaning into Arabic, but keep quoted evidence in its original language. Do not classify Arabic contract questions as unrelated general just because the contract text is English.

Return JSON only with: answer, plain_english_summary, practical_note, follow_up_suggestions.
Explanation language: {explanation_language}
If explanation_language is ar, write the direct answer, simple explanation, and practical note in clear simple Arabic. Keep quoted evidence in the original contract language.
Question type: {answer_type}
User question: {question}
Evidence: {evidence}
Selected contract excerpt: {contract_text[:10000]}
"""




def _validate_chat_answer(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        ChatAnswer(**{
            "answer": payload.get("answer", ""),
            "short_answer": payload.get("short_answer") or payload.get("plain_english_summary", ""),
            "confidence": float(payload.get("confidence") or 0),
            "intent": payload.get("intent") or payload.get("answer_type", "contract_specific"),
            "evidence": payload.get("evidence") or [],
            "missing_information": payload.get("missing_information") or [],
            "risk_note": payload.get("risk_note", "AI-assisted review only; not final legal advice."),
            "suggested_next_step": payload.get("suggested_next_step") or payload.get("practical_note", ""),
            "language": payload.get("language") or payload.get("response_language", "en"),
            "model_used": payload.get("model_used"),
            "degraded_mode": bool(payload.get("degraded_mode", True)),
            "is_legal_advice_disclaimer": bool(payload.get("is_legal_advice_disclaimer", True)),
        })
        payload["schema_validated"] = True
    except Exception as exc:
        payload["schema_validated"] = False
        payload["schema_validation_error"] = str(exc)
    return payload

def answer_question(contract_text: str, question: str, analysis: dict | None = None, explanation_language: str = "en"):
    answer_type = classify_question(question)
    if answer_type in {"small_talk", "app_help", "unrelated_general"}:
        return _general_answer(question, answer_type, explanation_language)
    evidence = retrieve_evidence(contract_text, question)
    settings = get_settings()
    if not getattr(settings, "ollama_enabled", True):
        return _fallback_contract_answer(question, evidence, answer_type, llm_unavailable=True, explanation_language=explanation_language)
    health = llm_health()
    if not health.get("reachable"):
        return _fallback_contract_answer(question, evidence, answer_type, llm_unavailable=True, explanation_language=explanation_language)
    try:
        ai = generate_structured_json(_chat_prompt(question, contract_text, evidence, answer_type, explanation_language), prompt_mode="chat", model=getattr(settings, "ollama_model", None))
        confidence = _confidence(evidence, answer_type)
        language = _chat_language(question, explanation_language)
        fallback = _fallback_contract_answer(question, evidence, answer_type, explanation_language=explanation_language)
        return _validate_chat_answer({"answer": ai.get("answer") or fallback["answer"], "short_answer": ai.get("plain_english_summary") or fallback["plain_english_summary"], "answer_type": answer_type, "intent": answer_type, "confidence": confidence, "confidence_label": _confidence_note_ar(confidence) if language == "ar" else _confidence_note(confidence), "used_contract": bool(evidence) or answer_type == "contract_specific", "evidence": evidence, "missing_information": [] if evidence else ["Contract evidence did not clearly answer the question."], "risk_note": "AI-assisted review only; not final legal advice.", "suggested_next_step": ai.get("practical_note") or fallback["practical_note"], "plain_english_summary": ai.get("plain_english_summary") or fallback["plain_english_summary"], "practical_note": ai.get("practical_note") or fallback["practical_note"], "follow_up_suggestions": ai.get("follow_up_suggestions") or _follow_ups_for_question(question, language), "degraded_mode": False, "llm_used": True, "model_used": getattr(settings, "ollama_model", None), "explanation_language": explanation_language, "response_language": language, "language": language, "is_legal_advice_disclaimer": True})
    except Exception:
        return _fallback_contract_answer(question, evidence, answer_type, llm_unavailable=True, explanation_language=explanation_language)


async def chat_with_contract(db, owner_user_id: str, contract: dict, question: str, explanation_language: str = "en"):
    latest = await db.analyses.find_one({"contract_id": str(contract["_id"]), "owner_user_id": owner_user_id}, sort=[("created_at", -1)])
    response = await asyncio.to_thread(answer_question, contract.get("extracted_text", ""), question, (latest or {}).get("analysis"), explanation_language)
    await db.chat_sessions.insert_one({"owner_user_id": owner_user_id, "contract_id": str(contract["_id"]), "question": question, "response": response, "created_at": datetime.now(timezone.utc)})
    return response
