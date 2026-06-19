"""Single grounded contract-analysis entrypoint.

This is the one place the redesigned upload -> analysis -> output flow calls into
the AI layer. It runs the evidence-grounded reasoning pipeline
(``run_contract_reasoning_pipeline``) with a *real* LLM callable wired in -- the
audit found that every existing caller invoked that pipeline without an
``llm_callable``, so its reviewer-verification / JSON-repair / model-reasoning
machinery never actually ran against the model and it silently degraded to a
deterministic stub.

Every returned section carries its own evidence citations and confidence, and the
whole payload is tagged ``degraded_mode`` when the model is unreachable, so the UI
can say so instead of presenting keyword output as a model judgement.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from backend.services.ollama_contract_ai import run_contract_reasoning_pipeline

logger = logging.getLogger(__name__)

JsonDict = Dict[str, Any]

# Canonical analysis sections the unified flow always produces, each mapped to the
# natural-language request the grounded pipeline classifies and retrieves against.
ANALYSIS_SECTIONS: Dict[str, str] = {
    "summary": "Summarize this contract in clear business English.",
    "risks": "What are the key risks and red flags in this contract?",
    "health": "Assess the overall health of this contract: missing clauses, "
    "one-sided terms, and what to review before signing.",
}


def make_llm_callable() -> Optional[Callable[[str], str]]:
    """Wrap the configured Ollama model as a plain ``str -> str`` callable.

    Returns ``None`` when the model is unreachable so the pipeline runs in its
    explicit deterministic-grounded mode rather than throwing. Importing the model
    lazily keeps this module cheap to import in tests that never call the LLM.
    """
    from backend.llm_config import llm_health_check

    if not llm_health_check().get("reachable"):
        return None

    from backend.gen1 import llm_model

    def _call(prompt: str) -> str:
        return str(llm_model.invoke(prompt).content)

    return _call


def _section_payload(section: str, question: str, contract_text: str,
                     llm_callable: Optional[Callable[[str], str]], debug: bool) -> JsonDict:
    reasoning = run_contract_reasoning_pipeline(
        question=question,
        contract_text=contract_text,
        llm_callable=llm_callable,
        debug=debug,
    )
    evidence: List[JsonDict] = [
        {"quote": item.get("quote", ""), "location": item.get("location", "")}
        for item in reasoning.get("evidence", [])
        if isinstance(item, dict)
    ]
    return {
        "section": section,
        "answer": reasoning.get("answer", ""),
        "confidence": reasoning.get("confidence", 0.0),
        "evidence": evidence,
        "risks": reasoning.get("risks", []),
        "missing_information": reasoning.get("missing_information", []),
        "debug": reasoning.get("debug") if debug else None,
    }


def run_grounded_analysis(
    contract_text: str,
    *,
    llm_callable: Optional[Callable[[str], str]] = None,
    debug: bool = False,
) -> JsonDict:
    """Produce the unified, evidence-grounded analysis for one contract.

    ``llm_callable`` is injectable so tests can run deterministically; in
    production the router passes :func:`make_llm_callable`. When it is ``None`` the
    whole result is flagged ``degraded_mode`` so the UI can render a clear banner.
    """
    text = (contract_text or "").strip()
    if not text:
        raise ValueError("contract_text is empty")

    degraded = llm_callable is None
    sections: Dict[str, JsonDict] = {
        name: _section_payload(name, question, text, llm_callable, debug)
        for name, question in ANALYSIS_SECTIONS.items()
    }

    confidences = [s["confidence"] for s in sections.values() if isinstance(s.get("confidence"), (int, float))]
    overall_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    return {
        "sections": sections,
        "overall_confidence": overall_confidence,
        "degraded_mode": degraded,
        "evaluation_source": "rule_based_fallback" if degraded else "llm",
    }
