from datetime import datetime, timezone
from typing import Any

from backend.services.llm_service import generate_structured_json, llm_health

CONTRACT_KEYWORDS = {"clause", "payment", "leave", "termination", "risk", "rights", "obligations", "liability", "confidential", "salary", "fee", "renewal", "governing", "negotiate", "contract", "agreement", "can i", "what does this mean", "summarize", "rewrite"}
SMALL_TALK = {"hi", "hello", "hey", "thanks", "thank you", "who are you"}
APP_HELP = {"how do i upload", "how do i analyze", "how does this app", "help", "what can you do"}


def classify_question(question: str) -> str:
    q = (question or "").lower().strip()
    if any(term in q for term in APP_HELP):
        return "app_help"
    if q in SMALL_TALK or any(q.startswith(term) for term in SMALL_TALK):
        return "small_talk"
    if any(term in q for term in CONTRACT_KEYWORDS):
        return "contract_specific"
    if any(term in q for term in ["what is", "explain", "define", "meaning of"]):
        return "general_contract_concept"
    return "unrelated_general"


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]


def retrieve_evidence(contract_text: str, question: str, limit: int = 4) -> list[dict[str, Any]]:
    q_words = [w.lower().strip("?.,:;()") for w in question.split() if len(w) > 3]
    evidence = []
    for sentence in _sentences(contract_text):
        lower = sentence.lower()
        score = sum(1 for word in q_words if word in lower)
        if score:
            evidence.append({"clause": "Relevant contract text", "text": sentence, "source": "extracted_contract_text", "location": "Extracted contract text", "score": score})
    evidence.sort(key=lambda item: item["score"], reverse=True)
    return evidence[:limit]


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


def _general_answer(question: str, answer_type: str, explanation_language: str = "en") -> dict[str, Any]:
    q = (question or "").strip()
    if answer_type == "small_talk":
        answer = "Hi — I can help you review the selected contract, explain clauses in plain English, identify risks, or answer general follow-up questions."
        summary = "You can ask about obligations, leave, payment, termination, risk, or negotiation points."
    elif answer_type == "app_help":
        answer = "Use the Contracts page to upload a document, then open Contract Analysis for a structured review or Contract Chat to ask questions about the selected contract."
        summary = "The app combines rule-based evidence extraction with AI-assisted explanations when the model is available."
    else:
        answer = f"Here is a general explanation: {q} is a concept I can discuss generally. If you want, I can also compare it to the selected contract."
        summary = "This answer is general and not based on the selected contract unless you ask me to compare it."
    if explanation_language == "ar":
        summary = "يمكنك طرح أسئلة عن الالتزامات أو الإجازة أو الدفع أو الإنهاء أو المخاطر أو نقاط التفاوض."
        practical_note = "إذا كان سؤالك عن العقد المحدد، اذكر الموضوع أو اسم البند المطلوب."
    else:
        practical_note = "If your question is about the selected contract, ask it with the relevant topic or clause name."
    return {"answer": answer, "answer_type": answer_type, "confidence": 0.7, "confidence_label": _confidence_note(0.7), "used_contract": False, "evidence": [], "plain_english_summary": summary, "practical_note": practical_note, "follow_up_suggestions": ["Summarize this contract", "What risks should I review first?", "Explain the key obligations", "What should I negotiate?"], "degraded_mode": False, "llm_used": False, "explanation_language": explanation_language}


def _fallback_contract_answer(question: str, evidence: list[dict[str, Any]], answer_type: str, llm_unavailable: bool = False, explanation_language: str = "en") -> dict[str, Any]:
    confidence = _confidence(evidence, answer_type)
    if evidence:
        evidence_text = evidence[0]["text"]
        answer = f"The contract appears to address this. In simple terms, the relevant text says: {evidence_text}"
        practical = "Review the quoted clause, confirm any approval steps or conditions, and ask the relevant business owner or counsel if the wording is unclear."
    else:
        answer = "I could not find contract evidence that clearly answers this question. The contract text provided does not show enough evidence to confirm this point."
        practical = "Ask for clarification or have the missing point added to the contract if it matters to the deal."
    if explanation_language == "ar":
        if evidence:
            answer = f"يبدو أن العقد يتناول هذا السؤال. ببساطة، النص المرتبط يقول: {evidence[0]['text']}"
            practical = "راجع النص المقتبس، وتأكد من أي شروط أو موافقات مطلوبة، واسأل صاحب العلاقة أو المستشار القانوني إذا كانت الصياغة غير واضحة."
        else:
            answer = "لم أجد دليلًا واضحًا في العقد يجيب عن هذا السؤال. النص المتاح لا يكفي لتأكيد هذه النقطة."
            practical = "اطلب توضيحًا أو أضف هذه النقطة إلى العقد إذا كانت مهمة للصفقة."
    if llm_unavailable:
        answer = ("نموذج الذكاء الاصطناعي غير متاح — تم عرض إجابة مبنية على القواعد. " if explanation_language == "ar" else "AI model unavailable — rule-based contract answer shown. ") + answer
    return {"answer": answer, "answer_type": answer_type, "confidence": confidence, "confidence_label": _confidence_note(confidence), "used_contract": True, "evidence": evidence, "plain_english_summary": answer, "practical_note": practical, "follow_up_suggestions": ["Show me the exact clause", "What does this mean in simple terms?", "Is this risky?", "What should I ask before signing?"], "degraded_mode": llm_unavailable, "llm_used": False, "explanation_language": explanation_language}


def _chat_prompt(question: str, contract_text: str, evidence: list[dict[str, Any]], answer_type: str, explanation_language: str = "en") -> str:
    return f"""
You are a helpful contract intelligence assistant. Speak naturally like ChatGPT. You can answer normal questions, small talk, and app questions. When the user asks about the selected contract, use only the contract text and extracted evidence. Do not invent contract facts. If the contract does not answer, say so clearly. Explain in simple language. Do not provide final legal advice. Give practical business-friendly next steps.

Return JSON only with: answer, plain_english_summary, practical_note, follow_up_suggestions.
Explanation language: {explanation_language}
If explanation_language is ar, write the direct answer, simple explanation, and practical note in clear simple Arabic. Keep quoted evidence in the original contract language.
Question type: {answer_type}
User question: {question}
Evidence: {evidence}
Selected contract excerpt: {contract_text[:10000]}
"""


def answer_question(contract_text: str, question: str, analysis: dict | None = None, explanation_language: str = "en"):
    answer_type = classify_question(question)
    if answer_type in {"small_talk", "app_help", "unrelated_general"}:
        return _general_answer(question, answer_type, explanation_language)
    evidence = retrieve_evidence(contract_text, question)
    health = llm_health()
    if not health.get("reachable"):
        return _fallback_contract_answer(question, evidence, answer_type, llm_unavailable=True, explanation_language=explanation_language)
    try:
        ai = generate_structured_json(_chat_prompt(question, contract_text, evidence, answer_type, explanation_language), retry_prompt=_chat_prompt(question, contract_text, evidence, answer_type, explanation_language) + "\nReturn valid JSON only.")
        confidence = _confidence(evidence, answer_type)
        return {"answer": ai.get("answer") or _fallback_contract_answer(question, evidence, answer_type, explanation_language=explanation_language)["answer"], "answer_type": answer_type, "confidence": confidence, "confidence_label": _confidence_note(confidence), "used_contract": bool(evidence) or answer_type == "contract_specific", "evidence": evidence, "plain_english_summary": ai.get("plain_english_summary") or "See the direct answer and evidence cards below.", "practical_note": ai.get("practical_note") or "Confirm important points with the business owner or counsel before relying on them.", "follow_up_suggestions": ai.get("follow_up_suggestions") or ["Show me the exact clause", "What should I negotiate?", "What is the risk?"], "degraded_mode": False, "llm_used": True, "explanation_language": explanation_language}
    except Exception:
        return _fallback_contract_answer(question, evidence, answer_type, llm_unavailable=True, explanation_language=explanation_language)


async def chat_with_contract(db, owner_user_id: str, contract: dict, question: str, explanation_language: str = "en"):
    latest = await db.analyses.find_one({"contract_id": str(contract["_id"]), "owner_user_id": owner_user_id}, sort=[("created_at", -1)])
    response = answer_question(contract.get("extracted_text", ""), question, (latest or {}).get("analysis"), explanation_language=explanation_language)
    await db.chat_sessions.insert_one({"owner_user_id": owner_user_id, "contract_id": str(contract["_id"]), "question": question, "response": response, "created_at": datetime.now(timezone.utc)})
    return response
