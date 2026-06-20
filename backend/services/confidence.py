"""One multi-factor confidence score, surfaced on every AI result.

Combines evidence volume, retrieval relevance, reviewer (grounding) approval, and
an ambiguity penalty into a single 0..1 score. Used identically by extraction,
health scoring, chat, and benchmarking so confidence means the same thing
everywhere it appears in the UI.
"""
from __future__ import annotations

from dataclasses import dataclass


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass
class ConfidenceInputs:
    evidence_count: int          # number of grounded evidence spans
    retrieval_relevance: float   # 0..1 relevance of retrieved context
    reviewer_approval: float     # 0..1 fraction of cited spans verified in source
    ambiguity_penalty: float     # 0..1 (higher = more uncertain / needs review)


def compute_confidence(inputs: ConfidenceInputs) -> float:
    evidence_factor = _clamp(inputs.evidence_count / 3.0)
    base = (
        0.30 * evidence_factor
        + 0.30 * _clamp(inputs.retrieval_relevance)
        + 0.40 * _clamp(inputs.reviewer_approval)
    )
    score = base * (1.0 - 0.5 * _clamp(inputs.ambiguity_penalty))
    return round(_clamp(score), 3)


def degraded_confidence(retrieval_relevance: float) -> float:
    """Confidence ceiling for deterministic (LLM-unavailable) results."""
    return round(min(0.4, 0.3 * _clamp(retrieval_relevance) + 0.1), 3)
