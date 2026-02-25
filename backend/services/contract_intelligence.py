"""Simple contract intelligence helpers used by API endpoints."""

from __future__ import annotations

from typing import Any, Dict


def extract_key_clauses(contract_text: str) -> Dict[str, Any]:
    text = (contract_text or "").strip()
    if not text:
        return {"chunks": [], "chunk_count": 0, "conflicts": []}

    chunks = [line.strip() for line in text.splitlines() if line.strip()]
    chunk_records = [
        {"chunk_id": idx + 1, "text": chunk[:500], "score": 1.0}
        for idx, chunk in enumerate(chunks[:50])
    ]
    return {"chunks": chunk_records, "chunk_count": len(chunk_records), "conflicts": []}


def answer_contract_question(
    contract_text: str, question: str, response_language: str = "english"
) -> Dict[str, Any]:
    text = (contract_text or "").strip()
    q = (question or "").strip()

    if not text or not q:
        return {
            "answer": "Not Found: missing contract text or question.",
            "evidence": [],
            "retrieved_chunk_ids": [],
            "retrieval_scores": [],
            "confidence": 0.0,
            "intent": "unknown",
            "not_found": ["missing_input"],
            "response_language": response_language,
        }

    # Naive lexical retrieval for deterministic local behavior.
    query_terms = [w.lower() for w in q.split() if len(w) > 2]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    scored = []
    for idx, line in enumerate(lines, start=1):
        low = line.lower()
        score = sum(1 for t in query_terms if t in low)
        if score:
            scored.append((score, idx, line))

    scored.sort(reverse=True)
    top = scored[:3]

    if not top:
        return {
            "answer": "Not Found: no grounded evidence for this question in the contract.",
            "evidence": [],
            "retrieved_chunk_ids": [],
            "retrieval_scores": [],
            "confidence": 0.0,
            "intent": "contract_qa",
            "not_found": ["no_evidence"],
            "response_language": response_language,
        }

    evidence = [{"chunk_id": idx, "text": line} for _, idx, line in top]
    retrieved_chunk_ids = [idx for _, idx, _ in top]
    retrieval_scores = [float(score) for score, _, _ in top]
    best_line = top[0][2]

    return {
        "answer": best_line,
        "evidence": evidence,
        "retrieved_chunk_ids": retrieved_chunk_ids,
        "retrieval_scores": retrieval_scores,
        "confidence": min(1.0, top[0][0] / max(1, len(query_terms))),
        "intent": "contract_qa",
        "not_found": [],
        "response_language": response_language,
    }
