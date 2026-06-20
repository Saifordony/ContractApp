"""The single grounded AI engine, reused by extraction, health, chat, benchmark.

One set of primitives — sentence-aware chunking, budget-aware retrieval, JSON
generation with a single repair retry, verbatim-quote verification with one
re-prompt on rejection, and a multi-factor confidence score — is composed into
every feature. When the LLM is unreachable, each feature returns the SAME shape
with ``degraded=True`` and a deterministic, retrieval-based result.
"""
from __future__ import annotations

import json
import re
from typing import AsyncIterator, Callable, Optional

from backend.config import get_settings
from backend.constants import (
    CLAUSE_STATUSES,
    CLAUSE_TYPES,
    HEALTH_DIMENSIONS,
    grade_from_score,
)
from backend.services.chunking import Chunk, chunk_text, estimate_tokens
from backend.services.confidence import (
    ConfidenceInputs,
    compute_confidence,
    degraded_confidence,
)
from backend.services.llm_client import LLMClient, LLMUnavailable, get_llm_client
from backend.services.prompts import chat_messages, extraction_messages, health_messages
from backend.services.retrieval import render_context, score_chunks, select_budgeted

PROMPT_OVERHEAD_TOKENS = 700
MAX_EXTRACTION_TOKENS = 1300
MAX_HEALTH_TOKENS = 900
MAX_CHAT_TOKENS = 700

_STATUS_SCORE = {"found": 1.0, "partially_found": 0.6, "needs_review": 0.4, "not_found": 0.0}
_STATUS_AMBIGUITY = {"found": 0.1, "partially_found": 0.4, "needs_review": 0.6, "not_found": 0.5}

# Fallback keyword hints per clause for the deterministic (LLM-down) path.
_CLAUSE_KEYWORDS = {
    "termination": "termination terminate notice end agreement إنهاء",
    "liability": "liability liable damages limitation cap مسؤولية",
    "confidentiality": "confidential confidentiality non-disclosure secret سرية",
    "payment": "payment fees invoice price pay net شروط الدفع",
    "renewal": "renewal renew auto-renew extend term تجديد",
    "intellectual_property": "intellectual property ip ownership copyright work product ملكية فكرية",
    "governing_law": "governing law jurisdiction governed by laws of قانون حاكم",
    "dispute_resolution": "dispute arbitration mediation court resolution نزاع تحكيم",
    "indemnification": "indemnify indemnification hold harmless تعويض",
    "force_majeure": "force majeure beyond control act of god قوة قاهرة",
}

_CORRECTION = (
    "Some quotes were not found verbatim in the CONTEXT. Re-extract using ONLY exact "
    "text copied character-for-character from the CONTEXT, or mark the clause "
    "needs_review/not_found with an empty quote."
)

ProgressFn = Callable[[str], "object"]  # async callable taking a status message


def _settings_model(degraded: bool) -> str:
    return "deterministic-fallback" if degraded else get_settings().ollama_model


def _budget(max_response: int) -> int:
    num_ctx = get_settings().ollama_num_ctx
    return max(512, num_ctx - PROMPT_OVERHEAD_TOKENS - max_response)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# --------------------------------------------------------------------------- #
# Grounding primitives
# --------------------------------------------------------------------------- #
_QUOTE_RE = re.compile(r'"([^"]{4,}?)"|“([^”]{4,}?)”|«([^»]{4,}?)»')


def _loads(text: str) -> dict:
    """Parse model output as JSON with one bounded structural repair."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


async def generate_json(llm: LLMClient, messages: list[dict], max_tokens: int) -> dict:
    """Call the model in JSON mode; on unparseable output, one repair retry.

    Raises ``LLMUnavailable`` on transport failure and ``ValueError`` if the output
    cannot be parsed even after the repair attempt.
    """
    raw = await llm.complete(messages, json_mode=True, max_tokens=max_tokens)
    try:
        return _loads(raw)
    except json.JSONDecodeError:
        repair = messages + [{
            "role": "user",
            "content": "Your previous reply was not valid JSON. Return ONLY the JSON object — no prose, no markdown fences.",
        }]
        raw2 = await llm.complete(repair, json_mode=True, max_tokens=max_tokens)
        try:
            return _loads(raw2)
        except json.JSONDecodeError as exc:
            raise ValueError("Model did not return valid JSON") from exc


def verify_span(source: str, quote: str) -> Optional[tuple[int, int, str]]:
    """Locate a quote verbatim in the source, tolerant of whitespace/case.

    Returns ``(start, end, matched_text)`` with real offsets, or ``None`` if the
    quote is not actually present (i.e. the model hallucinated it).
    """
    candidate = quote.strip().strip('"“”«»').strip()
    if len(candidate) < 4:
        return None
    idx = source.find(candidate)
    if idx != -1:
        return idx, idx + len(candidate), candidate
    parts = [re.escape(tok) for tok in candidate.split() if tok]
    if not parts:
        return None
    match = re.search(r"\s+".join(parts), source, flags=re.IGNORECASE)
    if match:
        return match.start(), match.end(), source[match.start():match.end()]
    return None


def _chunk_id_for(chunks: list[Chunk], start: int) -> Optional[int]:
    for chunk in chunks:
        if chunk.start <= start < chunk.end:
            return chunk.id
    return None


def extract_quotes(text: str) -> list[str]:
    quotes: list[str] = []
    for match in _QUOTE_RE.finditer(text):
        value = next((g for g in match.groups() if g), None)
        if value and value.strip() not in quotes:
            quotes.append(value.strip())
    return quotes


# --------------------------------------------------------------------------- #
# Clause extraction
# --------------------------------------------------------------------------- #
def _build_clauses(payload: dict, source: str, chunks: list[Chunk], relevance: float):
    by_key = {}
    for item in payload.get("clauses") or []:
        if isinstance(item, dict) and item.get("key"):
            by_key[str(item["key"]).strip()] = item

    clauses = []
    quoted = 0
    grounded = 0
    for clause_type in CLAUSE_TYPES:
        key = clause_type["key"]
        item = by_key.get(key, {})
        status = item.get("status")
        if status not in CLAUSE_STATUSES:
            status = "not_found"
        quote = str(item.get("quote") or "").strip()
        explanation = str(item.get("explanation") or "").strip()

        evidence = []
        if status != "not_found" and quote:
            quoted += 1
            span = verify_span(source, quote)
            if span:
                grounded += 1
                evidence = [{
                    "text": span[2], "char_start": span[0], "char_end": span[1],
                    "chunk_id": _chunk_id_for(chunks, span[0]),
                }]
            else:
                status = "needs_review"  # ungrounded quote -> demand review

        approval = 1.0 if (evidence or status == "not_found") else 0.0
        confidence = compute_confidence(ConfidenceInputs(
            evidence_count=len(evidence),
            retrieval_relevance=relevance,
            reviewer_approval=approval,
            ambiguity_penalty=_STATUS_AMBIGUITY[status],
        ))
        clauses.append({
            "key": key,
            "label": clause_type["label"],
            "status": status,
            "extracted_text": evidence[0]["text"] if evidence else "",
            "explanation": explanation,
            "evidence": evidence,
            "confidence": confidence,
        })

    approval_overall = (grounded / quoted) if quoted else 1.0
    return clauses, approval_overall


def _extraction_fallback(source: str, chunks: list[Chunk], relevance: float) -> list[dict]:
    clauses = []
    for clause_type in CLAUSE_TYPES:
        key = clause_type["key"]
        scored = score_chunks(_CLAUSE_KEYWORDS.get(key, key), chunks)
        best_chunk, best_score = (scored[0] if scored else (None, 0.0))
        if best_chunk is not None and best_score > 0.12:
            status = "needs_review"
            evidence = [{
                "text": best_chunk.text.strip()[:400], "char_start": best_chunk.start,
                "char_end": best_chunk.end, "chunk_id": best_chunk.id,
            }]
            explanation = ("AI is unavailable — this is the most relevant section found by "
                           "keyword search and needs human review.")
        else:
            status = "not_found"
            evidence = []
            explanation = "AI is unavailable — no relevant section found by keyword search."
        clauses.append({
            "key": key, "label": clause_type["label"], "status": status,
            "extracted_text": evidence[0]["text"] if evidence else "",
            "explanation": explanation, "evidence": evidence,
            "confidence": degraded_confidence(best_score),
        })
    return clauses


async def _extract(source: str, context: str, chunks: list[Chunk], language: str,
                   llm: LLMClient, relevance: float, emit: ProgressFn) -> tuple[list[dict], bool, float]:
    try:
        payload = await generate_json(llm, extraction_messages(context, language), MAX_EXTRACTION_TOKENS)
    except (LLMUnavailable, ValueError):
        return _extraction_fallback(source, chunks, relevance), True, 0.0

    clauses, approval = _build_clauses(payload, source, chunks, relevance)
    if approval < 1.0:
        await emit("Re-checking citations against the source…")
        try:
            payload2 = await generate_json(
                llm, extraction_messages(context, language, _CORRECTION), MAX_EXTRACTION_TOKENS)
            clauses2, approval2 = _build_clauses(payload2, source, chunks, relevance)
            if approval2 > approval:
                clauses, approval = clauses2, approval2
        except (LLMUnavailable, ValueError):
            pass
    return clauses, False, approval


# --------------------------------------------------------------------------- #
# Health scoring
# --------------------------------------------------------------------------- #
def _build_dimensions(payload: dict, source: str, chunks: list[Chunk], relevance: float):
    by_key = {}
    for item in payload.get("dimensions") or []:
        if isinstance(item, dict) and item.get("key"):
            by_key[str(item["key"]).strip()] = item

    dimensions = []
    grounded = 0
    quoted = 0
    for dim in HEALTH_DIMENSIONS:
        key = dim["key"]
        item = by_key.get(key, {})
        try:
            score = int(round(float(item.get("score", 0))))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(100, score))
        explanation = str(item.get("explanation") or "").strip()
        quote = str(item.get("quote") or "").strip()
        evidence = []
        if quote:
            quoted += 1
            span = verify_span(source, quote)
            if span:
                grounded += 1
                evidence = [{
                    "text": span[2], "char_start": span[0], "char_end": span[1],
                    "chunk_id": _chunk_id_for(chunks, span[0]),
                }]
        dimensions.append({
            "key": key, "label": dim["label"], "score": score,
            "explanation": explanation, "evidence": evidence,
        })
    approval = (grounded / quoted) if quoted else 0.5
    return dimensions, approval


def _health_fallback(clauses: list[dict], relevance: float) -> dict:
    by_key = {c["key"]: c["status"] for c in clauses}

    def avg(keys: list[str]) -> float:
        return _mean([_STATUS_SCORE[by_key.get(k, "not_found")] for k in keys]) * 100

    completeness = avg([c["key"] for c in CLAUSE_TYPES])
    risk = avg(["liability", "indemnification", "termination", "force_majeure"])
    enforceability = avg(["governing_law", "dispute_resolution"])
    clarity = min(100.0, completeness * 0.8 + 12)
    dim_scores = {
        "clarity": clarity, "risk_exposure": risk,
        "completeness": completeness, "enforceability": enforceability,
    }
    dimensions = [{
        "key": d["key"], "label": d["label"], "score": int(round(dim_scores[d["key"]])),
        "explanation": "AI is unavailable — heuristic score derived from detected clauses.",
        "evidence": [],
    } for d in HEALTH_DIMENSIONS]
    overall = int(round(_mean(list(dim_scores.values()))))
    return {
        "overall_score": overall, "grade": grade_from_score(overall),
        "dimensions": dimensions, "confidence": degraded_confidence(relevance),
    }


async def _health(source: str, context: str, chunks: list[Chunk], clauses: list[dict],
                  language: str, llm: LLMClient, relevance: float) -> tuple[dict, bool]:
    summary = "; ".join(f"{c['key']}={c['status']}" for c in clauses)
    try:
        payload = await generate_json(llm, health_messages(context, summary, language), MAX_HEALTH_TOKENS)
    except (LLMUnavailable, ValueError):
        return _health_fallback(clauses, relevance), True

    dimensions, approval = _build_dimensions(payload, source, chunks, relevance)
    try:
        overall = int(round(float(payload.get("overall_score"))))
    except (TypeError, ValueError):
        overall = int(round(_mean([d["score"] for d in dimensions])))
    overall = max(0, min(100, overall))
    evidence_count = sum(len(d["evidence"]) for d in dimensions)
    confidence = compute_confidence(ConfidenceInputs(
        evidence_count=evidence_count, retrieval_relevance=relevance,
        reviewer_approval=approval, ambiguity_penalty=0.2,
    ))
    return {
        "overall_score": overall, "grade": grade_from_score(overall),
        "dimensions": dimensions, "confidence": confidence,
    }, False


# --------------------------------------------------------------------------- #
# Public: analyze (extraction + health)
# --------------------------------------------------------------------------- #
async def _noop(_message: str) -> None:
    return None


async def analyze_contract(contract: dict, llm: Optional[LLMClient] = None,
                           emit: ProgressFn = _noop) -> dict:
    """Run the full grounded analysis (clause extraction + health) for a contract."""
    llm = llm or get_llm_client()
    language = contract.get("language", "en")
    source = contract["content"]

    await emit("Splitting the contract into sentences…")
    chunks = chunk_text(source)
    query = " ".join(_CLAUSE_KEYWORDS.values())
    scored = score_chunks(query, chunks)
    relevance = scored[0][1] if scored else 0.0
    selected = select_budgeted(scored, token_budget=_budget(MAX_EXTRACTION_TOKENS))
    context = render_context(selected)

    await emit("Extracting clauses with the model…")
    clauses, ext_degraded, ext_approval = await _extract(
        source, context, chunks, language, llm, relevance, emit)

    await emit("Scoring contract health…")
    health, health_degraded = await _health(
        source, context, chunks, clauses, language, llm, relevance)

    degraded = ext_degraded or health_degraded
    clause_conf = _mean([c["confidence"] for c in clauses]) if clauses else 0.0
    overall_conf = round((clause_conf + health["confidence"]) / 2, 3)
    return {
        "language": language,
        "degraded": degraded,
        "model": _settings_model(degraded),
        "confidence": overall_conf,
        "clauses": clauses,
        "health": health,
    }


# --------------------------------------------------------------------------- #
# Public: chat (streaming, grounded with verified citations)
# --------------------------------------------------------------------------- #
def _chat_fallback(question: str, chunks: list[Chunk], language: str, relevance: float) -> dict:
    scored = score_chunks(question, chunks)
    best = scored[0][0] if scored else None
    if best is None:
        msg = ("AI is unavailable and no relevant section was found." if language == "en"
               else "الذكاء الاصطناعي غير متاح ولم يتم العثور على قسم ذي صلة.")
        return {"content": msg, "citations": [], "confidence": degraded_confidence(0.0), "degraded": True}
    note = ("AI is unavailable. The most relevant section of the contract is shown below "
            "(keyword match, needs review):\n\n" if language == "en"
            else "الذكاء الاصطناعي غير متاح. فيما يلي أكثر قسم ذي صلة في العقد (مطابقة بالكلمات المفتاحية، يحتاج لمراجعة):\n\n")
    text = best.text.strip()
    return {
        "content": note + text,
        "citations": [{"text": text[:400], "char_start": best.start, "char_end": best.start + min(400, len(text))}],
        "confidence": degraded_confidence(relevance),
        "degraded": True,
    }


async def answer_question_stream(contract: dict, question: str,
                                 llm: Optional[LLMClient] = None,
                                 history: Optional[list[dict]] = None) -> AsyncIterator[dict]:
    """Stream a grounded chat answer. Yields ``{"type": "token", ...}`` events as
    the model produces prose, then a final ``{"type": "result", ...}`` event with
    verified citations, confidence, and the degraded flag."""
    llm = llm or get_llm_client()
    language = contract.get("language", "en")
    source = contract["content"]

    chunks = chunk_text(source)
    scored = score_chunks(question, chunks)
    relevance = scored[0][1] if scored else 0.0
    selected = select_budgeted(scored, token_budget=_budget(MAX_CHAT_TOKENS))
    context = render_context(selected)
    messages = chat_messages(context, question, language, history)

    full = ""
    try:
        async for token in llm.stream(messages, max_tokens=MAX_CHAT_TOKENS):
            full += token
            yield {"type": "token", "text": token}
    except LLMUnavailable:
        result = _chat_fallback(question, chunks, language, relevance)
        if not full:
            yield {"type": "token", "text": result["content"]}
        yield {"type": "result", "data": result}
        return

    citations = []
    for quote in extract_quotes(full):
        span = verify_span(source, quote)
        if span:
            citations.append({"text": span[2], "char_start": span[0], "char_end": span[1]})
    approval = 1.0 if citations else 0.0
    confidence = compute_confidence(ConfidenceInputs(
        evidence_count=len(citations), retrieval_relevance=relevance,
        reviewer_approval=approval, ambiguity_penalty=0.1 if citations else 0.4,
    ))
    yield {"type": "result", "data": {
        "content": full.strip(),
        "citations": citations,
        "confidence": confidence,
        "degraded": False,
    }}
