"""Evidence-grounded contract reasoning helpers for local Ollama workflows.

This module is deliberately deterministic by default.  It prepares the multi-step
contract-analysis workflow (task classification -> retrieval -> draft schema ->
review -> confidence) and can optionally be given a local Ollama callable by the
API layer.  Tests exercise the guardrails without requiring a live model.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional

from backend.services.contract_intelligence import (
    chunk_contract_text,
    retrieve_relevant_chunks_with_scores,
)

logger = logging.getLogger(__name__)

JsonDict = Dict[str, Any]
LlmCallable = Callable[[str], str]

CLAUSE_MEMORY_KEYS = [
    "payment_terms",
    "termination",
    "renewal",
    "liability",
    "indemnity",
    "confidentiality",
    "governing_law",
    "dispute_resolution",
    "obligations",
    "sla",
    "penalties",
    "change_control",
    "missing_clauses",
]

TASK_KEYWORDS = {
    "summary": {"summary", "summarize", "overview", "plain english"},
    "clause_extraction": {"extract", "clause", "clauses", "find terms"},
    "risk_review": {"risk", "risks", "red flag", "safe to sign", "review"},
    "contract_health": {"health", "score", "approved", "approval", "complete"},
    "benchmark_explanation": {"benchmark", "compare", "market", "peer", "outlier"},
    "missing_clause_check": {"missing", "absent", "not included", "not found"},
    "legal_commercial_qa": {"termination", "payment", "salary", "leave", "law", "liability", "notice"},
}

CONTRACT_ANALYST_SYSTEM = (
    "You are a senior contract analyst. Use only the contract evidence provided. "
    "Do not guess, do not invent legal facts, and do not use outside knowledge. "
    "Return JSON only and include direct evidence quotes. If evidence is missing, "
    "write 'Not found in the provided contract text.'"
)

PROMPT_TEMPLATES: Dict[str, str] = {
    "contract_summary": CONTRACT_ANALYST_SYSTEM + "\nTask: summarize the contract in business English. Evidence:\n{evidence}\nJSON schema: {schema}",
    "clause_extraction": CONTRACT_ANALYST_SYSTEM + "\nTask: extract only the requested clause from evidence. Evidence:\n{evidence}\nJSON schema: {schema}",
    "risk_analysis": CONTRACT_ANALYST_SYSTEM + "\nTask: identify contract risks and red flags from evidence. Evidence:\n{evidence}\nJSON schema: {schema}",
    "contract_health": CONTRACT_ANALYST_SYSTEM + "\nTask: explain contract health dimensions from evidence. Evidence:\n{evidence}\nJSON schema: {schema}",
    "benchmark_explanation": CONTRACT_ANALYST_SYSTEM + "\nTask: explain benchmark comparison using only supplied benchmark and contract evidence. Evidence:\n{evidence}\nJSON schema: {schema}",
    "user_question_answering": CONTRACT_ANALYST_SYSTEM + "\nUser question: {question}\nEvidence:\n{evidence}\nJSON schema: {schema}",
    "reviewer_verification": "You are a contract QA reviewer. Verify the answer is supported by evidence and return JSON only: {answer}",
    "json_repair": "Repair this into valid JSON matching the schema. Return JSON only. Schema: {schema}\nRaw output:\n{raw_output}",
}

REQUIRED_SCHEMA_KEYS = {
    "answer": str,
    "confidence": (int, float),
    "evidence": list,
    "risks": list,
    "missing_information": list,
}


def classify_contract_task(message: str) -> str:
    text = (message or "").lower()
    for task, keywords in TASK_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return task
    return "legal_commercial_qa"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_\-']+", (text or "").lower())


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def hybrid_retrieve_evidence(contract_text: str, query: str, top_k: int = 4) -> List[JsonDict]:
    """Retrieve relevant evidence using BM25-like lexical scoring plus exact-title boosts."""
    chunks = chunk_contract_text(contract_text)
    if not chunks:
        return []

    base_hits = retrieve_relevant_chunks_with_scores(query, chunks, top_k=max(top_k * 2, top_k))
    title_terms = {
        "termination", "renewal", "payment", "liability", "indemnity", "confidentiality",
        "governing law", "dispute", "resolution", "sla", "penalties", "obligations", "change control",
    }
    query_text = (query or "").lower()
    query_tokens = set(_tokenize(query_text))

    ranked: List[JsonDict] = []
    seen = set()
    for score, chunk in base_hits:
        chunk_text = chunk.text.strip()
        lower = chunk_text.lower()
        exact_title_boost = 0.0
        for term in title_terms:
            term_tokens = set(_tokenize(term))
            if (term in query_text or term_tokens & query_tokens) and term in lower:
                exact_title_boost += 0.18
        combined = min(1.0, _safe_float(score) + exact_title_boost)
        key = (chunk.chunk_id, chunk.start_offset, chunk.end_offset)
        if key in seen:
            continue
        seen.add(key)
        ranked.append({
            "quote": chunk_text[:1200],
            "location": chunk.location,
            "chunk_id": chunk.chunk_id,
            "relevance_score": round(combined, 4),
            "retrieval_method": "hybrid_keyword_bm25",
        })

    ranked.sort(key=lambda item: item["relevance_score"], reverse=True)
    return ranked[:top_k]


def build_clause_memory(contract_text: str, validated_clauses: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    memory: Dict[str, Any] = {key: [] for key in CLAUSE_MEMORY_KEYS if key != "missing_clauses"}
    missing: List[str] = []
    validated_clauses = validated_clauses or {}

    alias_map = {
        "liability": ["liability", "limitation_of_liability"],
        "obligations": ["obligations", "sla_obligations", "scope_of_work"],
        "sla": ["sla", "sla_obligations"],
        "indemnity": ["indemnity", "indemnification"],
    }

    for key in list(memory.keys()):
        candidates = alias_map.get(key, [key])
        for candidate in candidates:
            payload = validated_clauses.get(candidate)
            if isinstance(payload, dict) and payload.get("status") == "found" and payload.get("extracted_text"):
                memory[key].append({
                    "text": payload.get("extracted_text"),
                    "evidence": payload.get("evidence_snippets", []),
                    "source": "validated_clause",
                })
        if not memory[key]:
            evidence = hybrid_retrieve_evidence(contract_text, key.replace("_", " "), top_k=2)
            if evidence and evidence[0].get("relevance_score", 0) >= 0.28:
                memory[key].append({"text": evidence[0]["quote"], "evidence": evidence, "source": "retrieved_text"})
            else:
                missing.append(key)

    memory["missing_clauses"] = missing
    return memory


def parse_json_lenient(raw_output: Any) -> JsonDict:
    if isinstance(raw_output, dict):
        return raw_output
    text = str(raw_output or "").strip()
    if not text:
        raise ValueError("empty model output")
    if "```" in text:
        for block in text.split("```"):
            candidate = block.strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                text = candidate
                break
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    try:
        payload = json.loads(text)
    except Exception:
        payload = ast.literal_eval(text)
    if not isinstance(payload, dict):
        raise ValueError("model output must be a JSON object")
    return payload


def validate_ai_json_schema(payload: JsonDict) -> JsonDict:
    normalized = dict(payload or {})
    normalized.setdefault("answer", "Not found in the provided contract text.")
    normalized.setdefault("confidence", 0.0)
    normalized.setdefault("evidence", [])
    normalized.setdefault("risks", [])
    normalized.setdefault("missing_information", [])

    if not isinstance(normalized["answer"], str):
        normalized["answer"] = str(normalized["answer"])
    normalized["confidence"] = max(0.0, min(1.0, _safe_float(normalized["confidence"])))
    for key in ["evidence", "risks", "missing_information"]:
        if not isinstance(normalized[key], list):
            normalized[key] = [normalized[key]] if normalized[key] else []
    return normalized


def compute_confidence(
    *,
    evidence_count: int,
    best_relevance: float = 0.0,
    reviewer_approved: bool = True,
    inference_required: bool = False,
    ambiguous: bool = False,
) -> float:
    if evidence_count <= 0:
        return 0.05
    score = 0.25 + min(0.45, evidence_count * 0.12) + min(0.25, max(0.0, best_relevance) * 0.25)
    if reviewer_approved:
        score += 0.10
    else:
        score -= 0.30
    if inference_required:
        score -= 0.12
    if ambiguous:
        score -= 0.10
    return round(max(0.05, min(0.95, score)), 2)


def reviewer_verification(answer_payload: JsonDict, evidence: Iterable[JsonDict]) -> JsonDict:
    payload = validate_ai_json_schema(answer_payload)
    evidence_quotes = [str(item.get("quote", "")).strip() for item in evidence if isinstance(item, dict) and item.get("quote")]
    answer = payload.get("answer", "")
    if "not found in the provided contract text" in answer.lower():
        return {"approved": True, "feedback": "Missing-evidence answer is explicit.", "unsupported_claims": []}
    if not evidence_quotes:
        return {"approved": False, "feedback": "Answer has no supporting evidence quotes.", "unsupported_claims": [answer[:160]]}
    cited_quotes = payload.get("evidence", [])
    if not cited_quotes:
        return {"approved": False, "feedback": "Answer omitted evidence citations.", "unsupported_claims": [answer[:160]]}
    return {"approved": True, "feedback": "Answer includes evidence citations.", "unsupported_claims": []}


def _schema_text() -> str:
    return json.dumps({
        "answer": "string",
        "confidence": "number between 0 and 1",
        "evidence": [{"quote": "exact contract text", "location": "string"}],
        "risks": [{"title": "string", "severity": "low|medium|high", "reason": "string", "evidence": "exact quote"}],
        "missing_information": ["string"],
    })


def build_prompt(task: str, question: str, evidence: List[JsonDict]) -> str:
    evidence_text = "\n\n".join(
        f"[{idx + 1}] {item.get('location', 'unknown')} (score={item.get('relevance_score', 0)}):\n{item.get('quote', '')}"
        for idx, item in enumerate(evidence)
    ) or "No relevant evidence found."
    template_key = {
        "summary": "contract_summary",
        "risk_review": "risk_analysis",
        "missing_clause_check": "clause_extraction",
        "legal_commercial_qa": "user_question_answering",
    }.get(task, task)
    template = PROMPT_TEMPLATES.get(template_key, PROMPT_TEMPLATES["user_question_answering"])
    return template.format(question=question, evidence=evidence_text, schema=_schema_text())


def build_json_repair_prompt(raw_output: Any) -> str:
    """Build a strict local-model repair prompt for malformed JSON output."""
    return PROMPT_TEMPLATES["json_repair"].format(schema=_schema_text(), raw_output=str(raw_output or ""))


def build_deterministic_grounded_payload(question: str, evidence: List[JsonDict]) -> JsonDict:
    if not evidence:
        return validate_ai_json_schema({
            "answer": "Not found in the provided contract text.",
            "confidence": 0.05,
            "evidence": [],
            "risks": [],
            "missing_information": [question],
        })
    best = evidence[0]
    return validate_ai_json_schema({
        "answer": "Based on the retrieved contract evidence, review the cited text before relying on this point.",
        "confidence": compute_confidence(evidence_count=len(evidence), best_relevance=best.get("relevance_score", 0.0)),
        "evidence": [{"quote": item.get("quote", ""), "location": item.get("location", "")} for item in evidence[:3]],
        "risks": [],
        "missing_information": [],
    })


def run_contract_reasoning_pipeline(
    *,
    question: str,
    contract_text: str,
    llm_callable: Optional[LlmCallable] = None,
    debug: bool = False,
) -> JsonDict:
    task = classify_contract_task(question)
    evidence = hybrid_retrieve_evidence(contract_text, question, top_k=4)
    prompt = build_prompt(task, question, evidence)
    raw_output = None
    repaired = False

    if llm_callable and evidence:
        try:
            raw_output = llm_callable(prompt)
            payload = validate_ai_json_schema(parse_json_lenient(raw_output))
        except Exception:
            repaired = True
            try:
                repaired_output = llm_callable(build_json_repair_prompt(raw_output))
                payload = validate_ai_json_schema(parse_json_lenient(repaired_output))
                raw_output = repaired_output
            except Exception:
                payload = build_deterministic_grounded_payload(question, evidence)
    else:
        payload = build_deterministic_grounded_payload(question, evidence)

    review = reviewer_verification(payload, evidence)
    if not review.get("approved"):
        payload["confidence"] = compute_confidence(
            evidence_count=len(payload.get("evidence", [])),
            best_relevance=evidence[0].get("relevance_score", 0.0) if evidence else 0.0,
            reviewer_approved=False,
        )
        if not payload.get("evidence"):
            payload["answer"] = "Not found in the provided contract text."
            payload["missing_information"] = list(dict.fromkeys([*payload.get("missing_information", []), question]))

    if debug:
        logger.debug(
            "contract_reasoning_debug task=%s retrieved_chunks=%s raw_output_preview=%s reviewer=%s",
            task,
            [
                {
                    "location": item.get("location"),
                    "relevance_score": item.get("relevance_score"),
                    "quote_preview": str(item.get("quote", ""))[:160],
                }
                for item in evidence
            ],
            str(raw_output or "")[:500],
            review,
        )
        payload["debug"] = {
            "task": task,
            "retrieved_chunks": evidence,
            "prompt_preview": prompt[:1200],
            "raw_ollama_output": raw_output,
            "reviewer_feedback": review,
            "json_repaired_or_fallback": repaired,
        }
    return payload
