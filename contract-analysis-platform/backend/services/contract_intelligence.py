from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class TextChunk:
    chunk_id: str
    text: str
    location: str
    start_offset: int
    end_offset: int


SYNONYM_MAP: Dict[str, List[str]] = {
    "law": ["governing law", "jurisdiction", "laws"],
    "governs": ["governing", "jurisdiction"],
    "jurisdiction": ["governing law", "law", "governed"],
    "payment": ["invoice", "fee", "price", "compensation", "pay"],
    "terminate": ["termination", "end", "cancel"],
    "confidential": ["non-disclosure", "nda", "privacy"],
    "liability": ["damages", "cap", "indemnity"],
}


LEGAL_QUESTION_HINTS = {
    "contract", "clause", "agreement", "salary", "payment", "invoice", "leave",
    "vacation", "sick", "notice", "termination", "resignation", "overtime",
    "benefits", "working", "hours", "liability", "confidential", "governing", "law",
    "dispute", "arbitration", "renewal", "probation", "penalty", "obligation",
}

PERSONAL_NONLEGAL_HINTS = {
    "feel", "tired", "sad", "stressed", "depressed", "anxious", "tomorrow",
    "donot", "dont", "don't", "can i do", "what can i do", "life", "motivation",
}


@dataclass
class RetrievalHit:
    score: float
    chunk: TextChunk
    lexical_score: float
    semantic_score: float


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_\-']+", (text or "").lower())


def _expand_query_tokens(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    for token in list(tokens):
        for synonym in SYNONYM_MAP.get(token, []):
            expanded.update(_tokenize(synonym))
    return expanded


def chunk_contract_text(contract_text: str, chunk_size: int = 900) -> List[TextChunk]:
    text = (contract_text or "").strip()
    if not text:
        return []

    lines = [line.rstrip() for line in text.splitlines()]
    chunks: List[TextChunk] = []

    current = []
    current_heading = "Document"
    current_start = 0
    cursor = 0
    chunk_index = 1

    def flush_chunk(end_cursor: int):
        nonlocal chunk_index, current, current_start
        joined = "\n".join([l for l in current if l is not None]).strip()
        if not joined:
            return
        chunks.append(
            TextChunk(
                chunk_id=f"chunk-{chunk_index}",
                text=joined,
                location=f"section:{current_heading};offset:{current_start}-{end_cursor}",
                start_offset=current_start,
                end_offset=end_cursor,
            )
        )
        chunk_index += 1

    def is_heading(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        if re.match(r"^\d+(\.\d+)*\s+", stripped):
            return True
        if len(stripped) <= 90 and stripped.upper() == stripped and any(ch.isalpha() for ch in stripped):
            return True
        return False

    for line in lines:
        line_len = len(line) + 1
        if is_heading(line):
            if current:
                flush_chunk(cursor)
                current = []
            current_heading = line.strip()
            current_start = cursor

        current.append(line)
        joined_len = sum(len(l) + 1 for l in current)
        if joined_len >= chunk_size:
            flush_chunk(cursor + line_len)
            current = []
            current_start = cursor + line_len

        cursor += line_len

    if current:
        flush_chunk(cursor)

    return chunks


def _idf_lookup(chunks: List[TextChunk]) -> Dict[str, float]:
    total_docs = max(len(chunks), 1)
    doc_freq: Dict[str, int] = {}
    for chunk in chunks:
        unique = set(_tokenize(chunk.text))
        for tok in unique:
            doc_freq[tok] = doc_freq.get(tok, 0) + 1
    return {tok: math.log(1 + total_docs / (1 + df)) for tok, df in doc_freq.items()}


def retrieve_relevant_chunks_with_scores(
    question: str,
    chunks: List[TextChunk],
    top_k: int = 4,
) -> List[Tuple[float, TextChunk]]:
    base_tokens = set(_tokenize(question))
    q_tokens = _expand_query_tokens(base_tokens)
    if not q_tokens:
        return [(1.0, chunk) for chunk in chunks[:top_k]]

    idf = _idf_lookup(chunks)
    scored: List[RetrievalHit] = []
    q_lower = (question or "").lower()

    for chunk in chunks:
        c_tokens = _tokenize(chunk.text)
        if not c_tokens:
            continue

        c_token_set = set(c_tokens)
        overlap = q_tokens & c_token_set
        lexical = len(overlap) / max(len(q_tokens), 1)

        tf_bonus = 0.0
        for token in overlap:
            tf_bonus += min(0.12, c_tokens.count(token) * 0.02 * (1 + idf.get(token, 0.0)))

        phrase_bonus = 0.14 if q_lower and q_lower in chunk.text.lower() else 0.0

        semantic = 0.0
        for token in base_tokens:
            for syn in SYNONYM_MAP.get(token, []):
                syn_tokens = set(_tokenize(syn))
                if syn_tokens & c_token_set:
                    semantic += 0.06

        score = lexical + tf_bonus + phrase_bonus + semantic
        if score > 0:
            scored.append(
                RetrievalHit(
                    score=round(score, 4),
                    chunk=chunk,
                    lexical_score=round(lexical, 4),
                    semantic_score=round(semantic, 4),
                )
            )

    scored.sort(key=lambda item: item.score, reverse=True)
    return [(hit.score, hit.chunk) for hit in scored[:top_k]]


def retrieve_relevant_chunks(question: str, chunks: List[TextChunk], top_k: int = 4) -> List[TextChunk]:
    return [chunk for _, chunk in retrieve_relevant_chunks_with_scores(question, chunks, top_k)]


def _extract_sentences_with_keywords(text: str, question_tokens: set[str], limit: int = 3) -> List[str]:
    sentences = re.split(r"(?<=[\.!?])\s+", text)
    picked: List[str] = []
    for sentence in sentences:
        st = sentence.strip()
        if not st:
            continue
        st_tokens = set(_tokenize(st))
        if question_tokens & st_tokens:
            picked.append(st)
        if len(picked) >= limit:
            break
    return picked


def extract_key_clauses(contract_text: str) -> Dict[str, Any]:
    chunks = chunk_contract_text(contract_text)
    clause_map = {
        "parties": ["party", "parties", "between"],
        "effective_date": ["effective", "date"],
        "term": ["term", "duration"],
        "renewal": ["renew", "automatic renewal"],
        "termination": ["termination", "terminate"],
        "payment_terms": ["payment", "invoice", "fees"],
        "liability": ["liability", "damages", "limit"],
        "confidentiality": ["confidential", "confidentiality"],
        "governing_law": ["governing law", "law", "jurisdiction"],
        "dispute_resolution": ["dispute", "arbitration", "mediation"],
        "sla_obligations": ["service level", "sla", "obligation", "deliverable"],
        "penalties": ["penalty", "liquidated damages", "late fee"],
        "change_control": ["change", "amendment", "change order"],
    }

    extracted: Dict[str, Dict[str, Any]] = {}
    conflicts: List[Dict[str, Any]] = []

    for clause_name, keywords in clause_map.items():
        matches = []
        for chunk in chunks:
            lower = chunk.text.lower()
            if any(keyword in lower for keyword in keywords):
                matches.append(
                    {
                        "quote": chunk.text[:280],
                        "location": chunk.location,
                        "chunk_id": chunk.chunk_id,
                    }
                )

        if not matches:
            extracted[clause_name] = {
                "value": "Not Found",
                "evidence": [],
                "status": "missing",
            }
            continue

        extracted[clause_name] = {
            "value": matches[0]["quote"],
            "evidence": matches[:2],
            "status": "found",
        }

        unique_quotes = {m["quote"] for m in matches[:3]}
        if len(unique_quotes) > 1 and clause_name in {"term", "renewal", "payment_terms", "termination"}:
            conflicts.append(
                {
                    "clause": clause_name,
                    "status": "conflict",
                    "evidence": matches[:2],
                }
            )

    return {
        "clauses": extracted,
        "conflicts": conflicts,
        "chunk_count": len(chunks),
    }


def _build_risk_flags(text: str, evidence: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    lower = text.lower()
    flags: List[Dict[str, Any]] = []

    if "unlimited liability" in lower or "without limitation" in lower:
        flags.append({"type": "unlimited_liability", "severity": "high", "evidence": evidence[:1]})
    if "automatic renewal" in lower and "notice" not in lower:
        flags.append({"type": "auto_renewal_without_notice", "severity": "medium", "evidence": evidence[:1]})
    if "governing law" not in lower:
        flags.append({"type": "missing_governing_law", "severity": "high", "evidence": evidence[:1] if evidence else []})

    return flags


def _best_evidence_quotes(chunk: TextChunk, question_tokens: set[str], limit: int = 2) -> List[str]:
    sentences = re.split(r"(?<=[\.!?])\s+", chunk.text)
    ranked: List[Tuple[int, str]] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        tokens = set(_tokenize(sentence))
        score = len(tokens & question_tokens)
        if score > 0:
            ranked.append((score, sentence[:260]))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [sent for _, sent in ranked[:limit]]




def _is_out_of_scope_personal_question(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return True

    q_tokens = set(_tokenize(q))
    has_legal_signal = bool(q_tokens & LEGAL_QUESTION_HINTS)

    has_personal_signal = any(hint in q for hint in PERSONAL_NONLEGAL_HINTS)

    return has_personal_signal and not has_legal_signal


def answer_contract_question(contract_text: str, question: str) -> Dict[str, Any]:
    if _is_out_of_scope_personal_question(question):
        return {
            "answer": "I can only answer contract-related questions. I can’t give personal life advice.",
            "confidence": 0.0,
            "evidence": [],
            "not_found": [question],
            "follow_up_questions": [
                "Try asking: What does my contract say about leave, sick days, or notice?",
                "Try asking: Can I take unpaid leave and what notice is required?",
            ],
            "risk_flags": _build_risk_flags(contract_text, []),
            "retrieved_chunk_ids": [],
            "retrieval_scores": [],
        }

    chunks = chunk_contract_text(contract_text)
    scored_chunks = retrieve_relevant_chunks_with_scores(question, chunks)

    if not scored_chunks:
        return {
            "answer": "Not Found in the provided contract text.",
            "confidence": 0.0,
            "evidence": [],
            "not_found": [question],
            "follow_up_questions": ["Can you provide the exact clause title to check?"],
            "risk_flags": [],
            "retrieved_chunk_ids": [],
            "retrieval_scores": [],
        }

    top_score = scored_chunks[0][0]
    question_tokens = _expand_query_tokens(set(_tokenize(question)))

    if top_score < 0.28:
        return {
            "answer": "Not Found in the provided contract text.",
            "confidence": 0.1,
            "evidence": [],
            "not_found": [question],
            "follow_up_questions": [
                "Can you rephrase with a clause title (e.g., termination, payment, confidentiality)?",
                "Do you want me to list related clauses that might partially address this?",
            ],
            "risk_flags": _build_risk_flags(contract_text, []),
            "retrieved_chunk_ids": [chunk.chunk_id for _, chunk in scored_chunks],
            "retrieval_scores": [score for score, _ in scored_chunks],
        }

    evidence: List[Dict[str, str]] = []
    answer_sentences: List[str] = []

    for score, chunk in scored_chunks:
        best_quotes = _best_evidence_quotes(chunk, question_tokens, limit=2)
        if not best_quotes:
            continue
        for quote in best_quotes:
            evidence.append({"quote": quote, "location": chunk.location})
            answer_sentences.append(quote)

    answer_sentences = list(dict.fromkeys(answer_sentences))

    if not answer_sentences:
        answer = "Not Found in the provided contract text."
        confidence = 0.15
        not_found = [question]
    else:
        answer = "Based on your contract: " + " ".join(answer_sentences[:2])
        confidence = min(0.97, max(0.25, top_score))
        not_found = []

    follow_ups = [
        "Do you want me to summarize only the obligations that apply to you?",
        "Should I extract the exact clause text and provide a plain-language interpretation?",
    ]

    risk_flags = _build_risk_flags(contract_text, evidence)

    return {
        "answer": answer,
        "confidence": round(confidence, 2),
        "evidence": evidence[:3],
        "not_found": not_found,
        "follow_up_questions": follow_ups,
        "risk_flags": risk_flags,
        "retrieved_chunk_ids": [chunk.chunk_id for _, chunk in scored_chunks],
        "retrieval_scores": [score for score, _ in scored_chunks],
    }
