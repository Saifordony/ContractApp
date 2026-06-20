"""Evidence-grounded contract reasoning helpers for local Ollama workflows.

This module is deliberately deterministic by default.  It prepares the multi-step
contract-analysis workflow (task classification -> retrieval -> draft schema ->
review -> confidence) and can optionally be given a local Ollama callable by the
API layer.  Tests exercise the guardrails without requiring a live model.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional

from backend.services.contract_health import CLAUSE_KEYWORDS
from backend.services.contract_intelligence import (
    INTENT_KEYWORDS,
    LEGAL_QUESTION_HINTS,
    PERSONAL_NONLEGAL_HINTS,
    arabic_normalize,
    chunk_contract_text,
    retrieve_relevant_chunks_with_scores,
)
from backend.llm_config import OLLAMA_NUM_CTX

logger = logging.getLogger(__name__)

JsonDict = Dict[str, Any]
LlmCallable = Callable[[str], str]

# ---------------------------------------------------------------------------
# Tunable retrieval / pipeline constants
# ---------------------------------------------------------------------------
# Boost applied when a known clause-title term from the query also appears in a
# chunk.  Calibrated on employment and service-agreement samples where exact
# title matches (e.g. "Termination", "Governing Law") are strong relevance
# signals; exposed here so it can be tuned without editing function internals.
TITLE_MATCH_BOOST = 0.18

# When the best BM25 relevance is below this, run a character-trigram second
# pass to catch paraphrases that lexical overlap misses (no vector model needed).
SEMANTIC_FALLBACK_THRESHOLD = 0.20

# Dynamic retrieval breadth per classified task.  Complex, synthesis-heavy
# tasks need more evidence chunks; narrow lookups need fewer.
TOP_K_BY_TASK: Dict[str, int] = {
    "summary": 8,
    "risk_review": 6,
    "clause_extraction": 4,
    "legal_commercial_qa": 4,
    "contract_health": 10,
    "missing_clause_check": 3,
}
DEFAULT_TOP_K = 4

# Reasoning-pipeline retry / budget controls.
MAX_RETRIES = 2
TOKEN_BUDGET_RATIO = 0.85  # fraction of the context window the prompt may use

# Clause-memory: clauses retrieved below this relevance are kept but flagged
# low_confidence (amber) instead of being dropped as missing (red).
CLAUSE_MEMORY_RELEVANCE_THRESHOLD = 0.18

# Derive clause-memory keys from the contract_health keyword catalogue so the
# two files cannot drift out of sync (1.6 Problem B).
CLAUSE_MEMORY_KEYS = list(CLAUSE_KEYWORDS.keys()) + ["missing_clauses"]

TASK_KEYWORDS = {
    "summary": {"summary", "summarize", "overview", "plain english"},
    "clause_extraction": {"extract", "clause", "clauses", "find terms"},
    "risk_review": {"risk", "risks", "red flag", "safe to sign", "review"},
    "contract_health": {"health", "score", "approved", "approval", "complete"},
    "benchmark_explanation": {"benchmark", "compare", "market", "peer", "outlier"},
    "missing_clause_check": {"missing", "absent", "not included", "not found"},
    "legal_commercial_qa": {"termination", "payment", "salary", "leave", "law", "liability", "notice"},
}

# Intents from contract_intelligence that should resolve to evidence-grounded
# legal/commercial Q&A when the first-pass keyword match fails.
_INTENT_TO_TASK = "legal_commercial_qa"

OFF_TOPIC_REDIRECT = (
    "This question doesn't look like it's about the contract. I can help with "
    "clauses, risks, payment, termination, confidentiality, governing law, and "
    "other contract topics — try asking about one of those."
)

CONTRACT_ANALYST_SYSTEM = """You are a senior contract analyst with 15 years of experience reviewing commercial and employment agreements.

STRICT RULES:
1. Use ONLY the evidence provided between <evidence> tags. Never invent facts, dates, amounts, parties, or legal interpretations.
2. If the evidence does not answer the question, say exactly: "Not found in the provided contract text."
3. Your entire response must be valid JSON. Do not write anything outside the JSON object.
4. Every answer must include direct evidence quotes in the `evidence` field.
5. Classify every risk as: high (financial loss or legal liability), medium (ambiguity or one-sided terms), or low (minor or stylistic).

REASONING PROCESS (internal, not in output):
Step 1 — Understand what the question is really asking.
Step 2 — Identify which evidence chunks are most directly relevant.
Step 3 — Formulate a clear, evidence-backed answer.
Step 4 — Check: does every claim in your answer appear in the evidence? If not, remove it.
Step 5 — Output valid JSON matching the schema exactly."""


def _xml_template(task_instruction: str) -> str:
    """Compose an XML-structured prompt body shared by all analysis templates."""
    return (
        CONTRACT_ANALYST_SYSTEM
        + "\n\n<task>"
        + task_instruction
        + "\n{task_description}</task>\n"
        + "<evidence>\n{evidence}\n</evidence>\n"
        + "<output_schema>\n{schema}\n</output_schema>"
    )


PROMPT_TEMPLATES: Dict[str, str] = {
    "contract_summary": _xml_template("Summarize the contract in clear business English using only the evidence."),
    "clause_extraction": _xml_template("Extract only the requested clause(s) from the evidence, quoting exact wording."),
    "risk_analysis": _xml_template("Identify contract risks and red flags strictly from the evidence."),
    "contract_health": _xml_template("Explain the contract-health dimensions (risk, clarity, compliance, term, governing law) from the evidence."),
    "benchmark_explanation": _xml_template("Explain the benchmark comparison using only the supplied benchmark and contract evidence."),
    "user_question_answering": _xml_template("Answer the user's question about the contract using only the evidence."),
    "clause_rewrite": _xml_template(
        "Rewrite the cited clause to be clearer and more balanced for both parties. "
        "Quote the original text in `evidence`, then explain each change you made and why in `answer`."
    ),
    "missing_clause_suggestion": _xml_template(
        "The requested clause appears to be missing. Draft suggested language for it that fits the "
        "contract type and the jurisdiction/governing-law context visible in the other clauses. "
        "Mark clearly in `answer` that this is suggested drafting, not existing contract text."
    ),
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


def _tokenize(text: str) -> List[str]:
    # Includes the Arabic block and normalises script so bilingual queries match.
    return re.findall(r"[؀-ۿa-zA-Z0-9_\-']+", arabic_normalize((text or "").lower()))


def _keyword_matches(text: str, keyword: str) -> bool:
    """Substring match that is diacritic/spelling tolerant for Arabic."""
    return arabic_normalize(keyword) in text


def classify_contract_task(message: str) -> str:
    """Route a free-text request to an analysis task using a three-pass strategy.

    Pass 1: exact substring match against ``TASK_KEYWORDS``.
    Pass 2: token/substring overlap against ``INTENT_KEYWORDS`` (bilingual);
            any matched intent resolves to evidence-grounded legal/commercial Q&A.
    Pass 3: question-type heuristics — legal hint words default to
            ``legal_commercial_qa``; personal/non-legal hint words (with no legal
            signal) return ``off_topic`` so the caller can redirect without the LLM.
    """
    raw = message or ""
    text = arabic_normalize(raw.lower())

    # Pass 1 — explicit task keywords.
    for task, keywords in TASK_KEYWORDS.items():
        if any(_keyword_matches(text, keyword) for keyword in keywords):
            return task

    # Pass 2 — intent keyword overlap (token + Arabic substring).
    q_tokens = set(_tokenize(raw))
    best_intent: Optional[str] = None
    best_score = 0
    for intent, keywords in INTENT_KEYWORDS.items():
        kw_tokens = {tok for kw in keywords for tok in _tokenize(kw)}
        score = len(q_tokens & kw_tokens)
        score += sum(1 for kw in keywords if " " in kw and _keyword_matches(text, kw))
        if score > best_score:
            best_score = score
            best_intent = intent
    if best_intent and best_score > 0:
        return _INTENT_TO_TASK

    # Pass 3 — question-type heuristics.
    has_legal_signal = bool(q_tokens & {arabic_normalize(h) for h in LEGAL_QUESTION_HINTS})
    has_personal_signal = any(_keyword_matches(text, hint) for hint in PERSONAL_NONLEGAL_HINTS)
    if has_legal_signal:
        return "legal_commercial_qa"
    if has_personal_signal:
        return "off_topic"
    return "legal_commercial_qa"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _char_trigrams(text: str) -> set[str]:
    """Character trigrams over the normalised, space-collapsed text."""
    cleaned = re.sub(r"\s+", " ", arabic_normalize((text or "").lower())).strip()
    if len(cleaned) < 3:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + 3] for i in range(len(cleaned) - 2)}


def _content_hash(text: str) -> str:
    """Stable 16-hex content key for near-duplicate chunk deduplication."""
    return hashlib.sha256((text or "").strip().encode("utf-8")).hexdigest()[:16]


def hybrid_retrieve_evidence(contract_text: str, query: str, top_k: int = 4) -> List[JsonDict]:
    """Retrieve relevant evidence using BM25-like lexical scoring plus exact-title boosts.

    Falls back to character-trigram overlap when the best lexical score is weak,
    so paraphrased questions (e.g. "cap on what the company owes" vs "limitation
    of liability shall not exceed") still surface the right clause.
    """
    chunks = chunk_contract_text(contract_text)
    if not chunks:
        return []

    base_hits = retrieve_relevant_chunks_with_scores(query, chunks, top_k=max(top_k * 2, top_k))
    title_terms = {
        "termination", "renewal", "payment", "liability", "indemnity", "confidentiality",
        "governing law", "dispute", "resolution", "sla", "penalties", "obligations", "change control",
    }
    query_text = arabic_normalize((query or "").lower())
    query_tokens = set(_tokenize(query_text))

    ranked: List[JsonDict] = []
    seen: set[Any] = set()

    def _add(score: float, chunk: Any, method: str) -> None:
        chunk_text = chunk.text.strip()
        lower = arabic_normalize(chunk_text.lower())
        exact_title_boost = 0.0
        for term in title_terms:
            term_norm = arabic_normalize(term)
            term_tokens = set(_tokenize(term))
            if (term_norm in query_text or term_tokens & query_tokens) and term_norm in lower:
                exact_title_boost += TITLE_MATCH_BOOST
        combined = min(1.0, _safe_float(score) + exact_title_boost)
        # Content-hash dedup catches overlapping/re-chunked windows that share
        # text but have different offsets; positional key catches exact repeats.
        content_key = _content_hash(chunk_text)
        position_key = (chunk.chunk_id, chunk.start_offset, chunk.end_offset)
        if content_key in seen or position_key in seen:
            return
        seen.add(content_key)
        seen.add(position_key)
        ranked.append({
            "quote": chunk_text[:1200],
            "location": chunk.location,
            "chunk_id": chunk.chunk_id,
            "relevance_score": round(combined, 4),
            "retrieval_method": method,
        })

    for score, chunk in base_hits:
        _add(score, chunk, "hybrid_keyword_bm25")

    best_relevance_score = max((item["relevance_score"] for item in ranked), default=0.0)
    if best_relevance_score < SEMANTIC_FALLBACK_THRESHOLD:
        query_trigrams = _char_trigrams(query_text)
        # Only phrase-length queries benefit from trigram paraphrase matching;
        # single short words produce spurious suffix matches (e.g. "vacation"
        # sharing "ation" with "compensation"), so require enough trigrams.
        if len(query_trigrams) >= 8:
            trigram_hits: List[tuple[float, Any]] = []
            for chunk in chunks:
                chunk_trigrams = _char_trigrams(chunk.text)
                if not chunk_trigrams:
                    continue
                overlap = len(query_trigrams & chunk_trigrams) / max(len(query_trigrams), 1)
                # Require meaningful overlap so irrelevant chunks are not pulled in.
                if overlap >= 0.20:
                    trigram_hits.append((round(overlap, 4), chunk))
            trigram_hits.sort(key=lambda item: item[0], reverse=True)
            for score, chunk in trigram_hits[:top_k]:
                _add(score, chunk, "semantic_trigram_fallback")

    ranked.sort(key=lambda item: item["relevance_score"], reverse=True)
    return ranked[:top_k]


def build_clause_memory(contract_text: str, validated_clauses: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    memory: Dict[str, Any] = {key: [] for key in CLAUSE_MEMORY_KEYS if key != "missing_clauses"}
    missing: List[str] = []
    validated_clauses = validated_clauses or {}

    alias_map = {
        "limitation_of_liability": ["limitation_of_liability", "liability"],
        "scope_of_work": ["scope_of_work", "obligations", "sla_obligations"],
        "sla": ["sla", "sla_obligations"],
        "indemnification": ["indemnification", "indemnity"],
        "payment_terms": ["payment_terms", "payment"],
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
            if evidence:
                top_score = evidence[0].get("relevance_score", 0.0)
                record: Dict[str, Any] = {
                    "text": evidence[0]["quote"],
                    "evidence": evidence,
                    "source": "retrieved_text",
                }
                # Keep weak matches but flag them so the UI can render amber
                # (low confidence) instead of red (missing) — short contracts have
                # lower BM25 scores because IDF is less discriminative.
                if top_score < CLAUSE_MEMORY_RELEVANCE_THRESHOLD:
                    record["low_confidence"] = True
                memory[key].append(record)
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


# Map classified tasks to prompt templates.  ``clause_extraction`` and
# ``contract_health`` are now explicit (previously they silently fell through to
# user_question_answering).
_TASK_TO_TEMPLATE = {
    "summary": "contract_summary",
    "risk_review": "risk_analysis",
    "clause_extraction": "clause_extraction",
    "contract_health": "contract_health",
    "benchmark_explanation": "benchmark_explanation",
    "missing_clause_check": "clause_extraction",
    "legal_commercial_qa": "user_question_answering",
    "clause_rewrite": "clause_rewrite",
    "missing_clause_suggestion": "missing_clause_suggestion",
}

_TASK_DESCRIPTIONS = {
    "summary": "Provide a concise business summary of the contract.",
    "risk_review": "List the contract's risks and red flags.",
    "clause_extraction": "Extract the relevant clause(s).",
    "contract_health": "Assess the contract's health.",
    "benchmark_explanation": "Explain how the contract compares to the benchmark.",
    "missing_clause_check": "Identify which expected clauses are missing.",
}


def build_prompt(task: str, question: str, evidence: List[JsonDict]) -> str:
    numbered_evidence_chunks_with_locations = "\n\n".join(
        f"[{idx + 1}] {item.get('location', 'unknown')} (score={item.get('relevance_score', 0)}):\n{item.get('quote', '')}"
        for idx, item in enumerate(evidence)
    ) or "No relevant evidence found."
    template_key = _TASK_TO_TEMPLATE.get(task, "user_question_answering")
    template = PROMPT_TEMPLATES.get(template_key, PROMPT_TEMPLATES["user_question_answering"])
    # For Q&A the user's literal question is the task description; for the fixed
    # analysis tasks we use a short canonical instruction.
    if template_key == "user_question_answering":
        task_description = f"User question: {question}"
    else:
        task_description = _TASK_DESCRIPTIONS.get(task, question or "")
    return template.format(
        task_description=task_description,
        evidence=numbered_evidence_chunks_with_locations,
        schema=_schema_text(),
    )


def build_json_repair_prompt(raw_output: Any) -> str:
    """Build a strict local-model repair prompt for malformed JSON output."""
    return PROMPT_TEMPLATES["json_repair"].format(schema=_schema_text(), raw_output=str(raw_output or ""))


def _estimate_prompt_tokens(prompt: str) -> int:
    """Approximate token count for budget checks (~4 characters per token)."""
    return len(prompt or "") // 4


def build_off_topic_payload(question: str) -> JsonDict:
    """Deterministic redirect for clearly non-contract questions (no LLM call)."""
    return validate_ai_json_schema({
        "answer": OFF_TOPIC_REDIRECT,
        "confidence": 0.0,
        "evidence": [],
        "risks": [],
        "missing_information": [question] if question else [],
    })


def _targeted_reprompt(task: str, question: str, evidence: List[JsonDict]) -> str:
    """Re-prompt that forces the model to ground its answer in exact quotes."""
    quotes = "\n".join(f"- {item.get('quote', '')}" for item in evidence[:5] if item.get("quote"))
    base = build_prompt(task, question, evidence)
    return (
        base
        + "\n\nYour previous answer was not grounded in evidence. Here are the exact "
        "quotes you must use:\n"
        + quotes
        + "\nAnswer again using ONLY these quotes."
    )


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
    payload: Optional[JsonDict] = None

    # Clearly off-topic personal questions are redirected without any LLM call.
    if task == "off_topic":
        payload = build_off_topic_payload(question)
        if debug:
            payload["debug"] = {
                "task": task,
                "retrieved_chunks": [],
                "prompt_preview": "",
                "raw_ollama_output": None,
                "reviewer_feedback": {"approved": True, "feedback": "off_topic redirect"},
                "json_repaired_or_fallback": False,
            }
        return payload

    # Dynamic retrieval breadth driven by the classified task.
    top_k = TOP_K_BY_TASK.get(task, DEFAULT_TOP_K)
    evidence = hybrid_retrieve_evidence(contract_text, question, top_k=top_k)
    prompt = build_prompt(task, question, evidence)

    # Token-budget guard: if the prompt would approach the context window, shrink
    # the retrieved evidence and rebuild before calling the model.
    token_budget_reduced = False
    if evidence and _estimate_prompt_tokens(prompt) > OLLAMA_NUM_CTX * TOKEN_BUDGET_RATIO:
        reduced_top_k = max(1, top_k - 2)
        evidence = hybrid_retrieve_evidence(contract_text, question, top_k=reduced_top_k)
        prompt = build_prompt(task, question, evidence)
        token_budget_reduced = True

    raw_output = None
    recovered = False  # True if the first attempt didn't directly yield valid JSON

    if llm_callable and evidence:
        for attempt in range(MAX_RETRIES + 1):
            try:
                raw_output = llm_callable(prompt)
                payload = validate_ai_json_schema(parse_json_lenient(raw_output))
                break
            except Exception:
                recovered = True
                if attempt == MAX_RETRIES:
                    # Final attempt failed — try a one-shot JSON repair, then fall
                    # back to a deterministic grounded payload.
                    try:
                        repaired_output = llm_callable(build_json_repair_prompt(raw_output))
                        payload = validate_ai_json_schema(parse_json_lenient(repaired_output))
                        raw_output = repaired_output
                    except Exception:
                        payload = build_deterministic_grounded_payload(question, evidence)
                # else: transient failure — retry the same prompt.
        if payload is None:
            payload = build_deterministic_grounded_payload(question, evidence)
    else:
        payload = build_deterministic_grounded_payload(question, evidence)

    review = reviewer_verification(payload, evidence)

    # Reviewer-failure recovery: one targeted re-prompt that forces the model to
    # answer using only the exact evidence quotes.
    if not review.get("approved") and llm_callable and evidence:
        try:
            reprompt_output = llm_callable(_targeted_reprompt(task, question, evidence))
            reprompt_payload = validate_ai_json_schema(parse_json_lenient(reprompt_output))
            reprompt_review = reviewer_verification(reprompt_payload, evidence)
            recovered = True
            if reprompt_review.get("approved"):
                payload = reprompt_payload
                raw_output = reprompt_output
                review = reprompt_review
        except Exception:
            pass

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
            "top_k": top_k,
            "token_budget_reduced": token_budget_reduced,
            "retrieved_chunks": evidence,
            "prompt_preview": prompt[:1200],
            "raw_ollama_output": raw_output,
            "reviewer_feedback": review,
            "json_repaired_or_fallback": recovered,
        }
    return payload
