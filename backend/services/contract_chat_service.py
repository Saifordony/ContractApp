from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.services.contract_intelligence import (
    chunk_contract_text,
    retrieve_relevant_chunks_with_scores,
)
from backend.services.ollama_contract_ai import (
    build_clause_memory,
    run_contract_reasoning_pipeline,
)

DISCLAIMER = "AI-assisted review only — not legal advice."

CONTRACT_CHAT_SYSTEM_PROMPT = """
You are an AI contract assistant.
You help users understand the uploaded contract in plain English.
You are conversational, clear, and helpful.
You are not a lawyer and do not provide final legal advice.
You must answer only using the provided contract evidence.
If the contract evidence does not answer the question, say so clearly.
Do not invent clauses, dates, amounts, parties, obligations, or legal interpretations.
When possible, cite the evidence snippets.
If the user asks a short or vague question, infer the likely contract-related intent and answer helpfully.
If the user asks something unrelated to the contract, politely redirect them.

Answer style:
- Natural and conversational
- Clear and concise
- Use bullets for multi-point answers
- Explain legal terms simply
- Prioritize what matters to the user
- Include recommended next questions when helpful
"""

DEFAULT_FOLLOWUPS = [
    "What clauses are missing?",
    "What are the main risks?",
    "Does this contract mention termination?",
]

CLAUSE_SYNONYMS: Dict[str, List[str]] = {
    "leave_policy": ["vacation", "leave", "annual leave", "paid leave", "sick leave", "holiday", "holidays"],
    "compensation": ["salary", "compensation", "remuneration", "pay", "wage", "wages", "bonus", "commission"],
    "termination": ["termination", "terminate", "firing", "dismissal", "quitting", "resignation", "notice"],
    "governing_law": ["law", "governing law", "jurisdiction", "country"],
    "dispute_resolution": ["dispute", "arbitration", "court", "mediation"],
    "confidentiality": ["confidential", "confidentiality", "secret", "secrets", "nda", "non-disclosure"],
    "intellectual_property": ["ip", "intellectual property", "ownership", "work product"],
    "working_hours": ["hours", "working hours", "schedule", "overtime", "shift"],
    "probation": ["probation", "trial period"],
    "non_compete": ["non compete", "non-compete", "competitor", "competition"],
    "parties": ["parties", "party", "employer", "employee", "client", "contractor"],
    "payment_terms": ["invoice", "payment terms", "due date", "late payment", "fees"],
    "renewal": ["renewal", "renew", "extension"],
    "scope_of_work": ["scope", "responsibilities", "duties", "deliverables", "services"],
}

QUESTION_SIGNALS = {
    "contract", "clause", "clauses", "risk", "risks", "missing", "summarize", "summary",
    "safe", "sign", "fix", "review", "termination", "salary", "vacation", "leave",
    "law", "dispute", "confidential", "benchmark", "score", "readiness", "payment",
    "hours", "probation", "party", "parties", "obligation", "obligations",
}

GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "مرحبا", "اهلا"}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_\-']+", (text or "").lower())


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _title_clause(key: str) -> str:
    return key.replace("_", " ").title()


def classify_chat_intent(message: str) -> Tuple[str, Optional[str]]:
    q = _norm(message)
    if not q:
        return "clarification_needed", None
    if q in GREETINGS or q.rstrip("!.") in GREETINGS:
        return "greeting", None
    if any(word in q for word in ["summarize", "summary", "overview", "what is this contract"]):
        return "summarize_contract", None
    if any(word in q for word in ["missing", "not included", "clauses are absent"]):
        return "missing_clauses", None
    if any(word in q for word in ["risk", "risks", "safe to sign", "safe", "red flag", "red flags"]):
        return "risk_review", None
    if any(word in q for word in ["fix", "change first", "improve", "review before signing", "what should i review"]):
        return "recommendation", None
    if any(word in q for word in ["benchmark", "market", "compare", "comparison"]):
        return "benchmark_question", None
    if any(word in q for word in ["score", "readiness", "approved", "approval", "health"]):
        return "readiness_question", None

    for clause_key, synonyms in CLAUSE_SYNONYMS.items():
        if clause_key.replace("_", " ") in q or any(s in q for s in synonyms):
            return "clause_lookup", clause_key

    tokens = set(_tokenize(q))
    if tokens and not (tokens & QUESTION_SIGNALS) and len(tokens) > 3:
        return "unrelated", None
    if len(tokens) <= 2:
        return "clarification_needed", None
    return "evidence_question", None


def _empty_response(answer: str, answer_type: str, confidence: str = "Low", followups: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "answer": answer,
        "answer_type": answer_type,
        "confidence": confidence,
        "evidence_snippets": [],
        "suggested_followups": followups or DEFAULT_FOLLOWUPS,
        "limitations": DISCLAIMER,
        "debug": None,
    }


def _extract_structured_clauses(analysis_results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    structured = (analysis_results or {}).get("structured_clauses", {})
    clauses = structured.get("clauses", {}) if isinstance(structured, dict) else {}
    if isinstance(clauses, dict):
        return clauses
    return {}


def _found_clause_text(payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    if payload.get("status") != "found":
        return None
    text = payload.get("extracted_text")
    return str(text).strip() if text else None


def _evidence_from_clause(clause_name: str, payload: Dict[str, Any]) -> List[Dict[str, str]]:
    snippets = payload.get("evidence_snippets") or []
    evidence: List[Dict[str, str]] = []
    if isinstance(snippets, list):
        for item in snippets[:3]:
            if isinstance(item, dict) and item.get("quote"):
                evidence.append({
                    "quote": str(item.get("quote", "")),
                    "clause_name": _title_clause(clause_name),
                    "location": str(item.get("location", "Extracted clause")),
                    "relevance": "Validated extracted clause",
                })
    text = _found_clause_text(payload)
    if text and not evidence:
        evidence.append({
            "quote": text,
            "clause_name": _title_clause(clause_name),
            "location": "Extracted clause",
            "relevance": "Validated extracted clause",
        })
    return evidence


def _search_clause(clauses: Dict[str, Dict[str, Any]], clause_key: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
    payload = clauses.get(clause_key)
    text = _found_clause_text(payload)
    if text and isinstance(payload, dict):
        return text, _evidence_from_clause(clause_key, payload)
    return None, []


def _raw_text_evidence(contract_text: str, message: str, limit: int = 3) -> List[Dict[str, str]]:
    chunks = chunk_contract_text(contract_text)
    hits = retrieve_relevant_chunks_with_scores(message, chunks, top_k=limit)
    evidence: List[Dict[str, str]] = []
    for score, chunk in hits:
        if score <= 0:
            continue
        evidence.append({
            "quote": chunk.text[:700],
            "clause_name": "Contract Text",
            "location": chunk.location,
            "relevance": f"Raw text match ({score:.2f})",
        })
    return evidence


def _missing_clause_names(clauses: Dict[str, Dict[str, Any]], health: Dict[str, Any]) -> List[str]:
    missing = health.get("missing_critical_clauses", []) if isinstance(health, dict) else []
    names = [str(x) for x in missing if x]
    for key, payload in clauses.items():
        if isinstance(payload, dict) and payload.get("status") in {"not_found", "missing"}:
            names.append(_title_clause(key))
    return list(dict.fromkeys(names))[:10]


def build_contract_chat_response(
    *,
    message: str,
    contract_text: str,
    analysis_results: Optional[Dict[str, Any]] = None,
    benchmark_result: Optional[Dict[str, Any]] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    analysis_results = analysis_results or {}
    benchmark_result = benchmark_result or {}
    chat_history = chat_history or []
    intent, clause_key = classify_chat_intent(message)
    clauses = _extract_structured_clauses(analysis_results)
    health = analysis_results.get("health_evaluation", {}) if isinstance(analysis_results, dict) else {}
    clause_memory = build_clause_memory(contract_text, clauses) if contract_text else {"missing_clauses": []}

    if intent == "greeting":
        response = _empty_response(
            "Hi — I can help you review this contract. You can ask me things like: what clauses are missing, what risks I see, whether leave/vacation is mentioned, or what you should review before signing.",
            "greeting",
            "High",
            ["What clauses are missing?", "What are the main risks?", "Does this contract mention vacation?"],
        )
    elif intent == "unrelated":
        response = _empty_response(
            "I’m focused on this uploaded contract. Ask me about clauses, risks, obligations, missing terms, termination, compensation, leave, confidentiality, or benchmark gaps.",
            "unrelated",
            "High",
        )
    elif intent == "clarification_needed":
        response = _empty_response(
            "I can help with that — are you asking about a specific contract clause, a risk, missing terms, or what to review before signing?",
            "clarification",
            "Low",
            ["Explain termination", "Does this mention vacation?", "What should I fix first?"],
        )
    elif intent == "clause_lookup" and clause_key:
        text, evidence = _search_clause(clauses, clause_key)
        if text:
            response = {
                "answer": f"Yes — I found a {_title_clause(clause_key)} section. In plain English: this part of the contract deals with {clause_key.replace('_', ' ')}. Review the wording below carefully because this is the contract evidence I found.",
                "answer_type": "grounded_answer",
                "confidence": "High",
                "evidence_snippets": evidence,
                "suggested_followups": [f"Explain {_title_clause(clause_key)}", "What should I watch out for?", "What should I fix first?"],
                "limitations": DISCLAIMER,
                "debug": None,
            }
        else:
            reasoning = run_contract_reasoning_pipeline(
                question=message,
                contract_text=contract_text,
                debug=debug,
            )
            raw_evidence = [
                {
                    "quote": item.get("quote", ""),
                    "clause_name": "Contract Text",
                    "location": item.get("location", "Contract evidence"),
                    "relevance": "Hybrid retrieved evidence",
                }
                for item in reasoning.get("evidence", [])[:2]
            ]
            has_support = bool(raw_evidence) and not str(reasoning.get("answer", "")).lower().startswith("not found")
            response = {
                "answer": (
                    f"You’re probably asking whether the contract includes {_title_clause(clause_key).lower()}. "
                    + (reasoning.get("answer") if has_support else "I could not find reliable evidence for that in the uploaded contract. If this term matters, consider adding a clear clause for it before signing.")
                ),
                "answer_type": "grounded_answer" if has_support else "missing_evidence",
                "confidence": "Medium" if has_support else "Low",
                "evidence_snippets": raw_evidence,
                "suggested_followups": ["What clauses are missing?", "What should I fix first?", "What are the main risks?"],
                "limitations": DISCLAIMER,
                "debug": reasoning.get("debug") if debug else None,
            }
    elif intent == "missing_clauses":
        missing = _missing_clause_names(clauses, health)
        if missing:
            answer = "Here are the clauses or terms I could not verify from the available contract evidence:\n" + "\n".join(f"- {name}" for name in missing[:8])
        else:
            answer = "I did not find a confirmed missing-clause list in the current analysis. I can still answer from extracted clauses, but run Contract Readiness Review for a fuller missing-terms check."
        response = _empty_response(answer, "grounded_answer" if missing else "missing_evidence", "Medium")
    elif intent in {"risk_review", "readiness_question"}:
        issues = health.get("issues", []) if isinstance(health, dict) else []
        required = health.get("required_changes", []) if isinstance(health, dict) else []
        missing = _missing_clause_names(clauses, health)
        lines = ["I can’t give final legal advice, but based on the available contract evidence, here are the main review points:"]
        for item in list(issues)[:5]:
            lines.append(f"- Risk: {item}")
        for item in list(required)[:5]:
            lines.append(f"- Suggested fix: {item}")
        for item in missing[:5]:
            lines.append(f"- Missing or unclear: {item}")
        if len(lines) == 1:
            lines.append("- I do not see a completed readiness review yet. Run Contract Readiness Review for a stronger risk breakdown.")
        response = _empty_response("\n".join(lines), "grounded_answer", "Medium", ["What should I fix first?", "What clauses are missing?", "Explain termination"])
    elif intent == "recommendation":
        required = health.get("required_changes", []) if isinstance(health, dict) else []
        missing = _missing_clause_names(clauses, health)
        lines = ["Here’s what I’d review first, based only on the contract evidence available:", "\nCritical fixes:"]
        lines.extend([f"- {x}" for x in (list(required)[:4] or missing[:4] or ["Run Contract Readiness Review to identify critical fixes."])])
        lines.append("\nRecommended improvements:")
        lines.extend([f"- Clarify any missing or weak clauses such as {x}." for x in missing[:3]] or ["- Confirm key business terms like payment, termination, confidentiality, and governing law are clear."])
        lines.append("\nItems to confirm with legal counsel:")
        lines.append("- Whether the obligations, liability, termination rights, and local-law requirements are acceptable for your situation.")
        response = _empty_response("\n".join(lines), "grounded_answer", "Medium")
    elif intent == "benchmark_question":
        if benchmark_result:
            overall = benchmark_result.get("overall_position", {}) if isinstance(benchmark_result, dict) else {}
            score = overall.get("alignment_score") or benchmark_result.get("overall_score") or benchmark_result.get("score")
            position = overall.get("position_label")
            gaps = benchmark_result.get("gaps", []) if isinstance(benchmark_result, dict) else []
            answer = "I found benchmark information for this contract."
            if score is not None:
                answer += f" Benchmark Alignment Score: {score}/100."
            if position:
                answer += f" Position: {position}."
            if gaps:
                answer += " Biggest benchmark gaps: " + "; ".join(str(g) for g in gaps[:3])
            else:
                answer += " Review benchmark gaps before signing."
            response = _empty_response(answer, "grounded_answer", "Medium", ["What should I fix first?", "Why is the score low?", "What benchmark gaps matter most?"])
        else:
            response = _empty_response(
                "I can answer from the extracted clauses. For a fuller benchmark comparison, run Benchmark Comparison first.",
                "missing_evidence",
                "Low",
                ["What are the main risks?", "What clauses are missing?", "What should I review before signing?"],
            )
    elif intent == "summarize_contract":
        found = [(key, _found_clause_text(payload)) for key, payload in clauses.items()]
        found = [(key, text) for key, text in found if text]
        if found:
            lines = ["Here is a plain-English summary based on the extracted contract clauses:"]
            for key, text in found[:6]:
                short = text[:180].strip().replace("\n", " ")
                lines.append(f"- {_title_clause(key)}: {short}{'...' if len(text) > 180 else ''}")
            response = _empty_response("\n".join(lines), "grounded_answer", "Medium")
        else:
            evidence = _raw_text_evidence(contract_text, message, limit=3)
            response = {
                **_empty_response("Here is a high-level summary from the available contract text. I recommend running clause analysis for a cleaner summary.", "grounded_answer", "Low"),
                "evidence_snippets": evidence,
            }
    else:
        reasoning = run_contract_reasoning_pipeline(
            question=message,
            contract_text=contract_text,
            debug=debug,
        )
        evidence = [
            {
                "quote": item.get("quote", ""),
                "clause_name": "Contract Text",
                "location": item.get("location", "Contract evidence"),
                "relevance": "Hybrid retrieved evidence",
            }
            for item in reasoning.get("evidence", [])[:3]
        ]
        if evidence and not str(reasoning.get("answer", "")).lower().startswith("not found"):
            response = {
                "answer": reasoning.get("answer") or "I found contract text that appears relevant. Review the quoted evidence below before relying on this point.",
                "answer_type": "grounded_answer",
                "confidence": "High" if reasoning.get("confidence", 0) >= 0.75 else "Medium",
                "evidence_snippets": evidence,
                "suggested_followups": DEFAULT_FOLLOWUPS,
                "limitations": DISCLAIMER,
                "debug": reasoning.get("debug") if debug else None,
            }
        else:
            response = _empty_response(
                "I could not find reliable evidence for that in the uploaded contract.",
                "missing_evidence",
                "Low",
            )

    if debug:
        response["debug"] = {
            "intent": intent,
            "clause_key": clause_key,
            "history_count": len(chat_history),
            "has_analysis": bool(analysis_results),
            "has_benchmark": bool(benchmark_result),
            "clause_memory_missing": clause_memory.get("missing_clauses", []),
        }
    return response
