from datetime import datetime, timezone


def answer_question(contract_text: str, question: str, analysis: dict | None = None):
    q = (question or "").lower()
    text = contract_text or ""
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    keywords = [w for w in q.split() if len(w) > 3]
    matches = [s for s in sentences if any(k in s.lower() for k in keywords)][:3]
    if matches:
        return {"answer": "Based on the contract text: " + " ".join(matches), "confidence": 0.78, "evidence": [{"text": m} for m in matches], "risks": (analysis or {}).get("risks", [])[:3], "follow_up_suggestions": ["What risks should I negotiate?", "Summarize the payment obligations.", "Which clauses are missing?"], "degraded_mode": False}
    return {"answer": "I could not find supporting evidence in this contract for that question.", "confidence": 0.25, "evidence": [], "risks": [], "follow_up_suggestions": ["Ask about payment terms", "Ask about termination", "Ask about liability"], "degraded_mode": True}

async def chat_with_contract(db, owner_user_id: str, contract: dict, question: str):
    latest = await db.analyses.find_one({"contract_id": str(contract["_id"]), "owner_user_id": owner_user_id}, sort=[("created_at", -1)])
    response = answer_question(contract.get("extracted_text", ""), question, (latest or {}).get("analysis"))
    await db.chat_sessions.insert_one({"owner_user_id": owner_user_id, "contract_id": str(contract["_id"]), "question": question, "response": response, "created_at": datetime.now(timezone.utc)})
    return response
