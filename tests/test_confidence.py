"""Tests for the confidence scoring function."""
from __future__ import annotations

from backend.services.confidence import (
    ConfidenceInputs,
    compute_confidence,
    degraded_confidence,
)


def test_confidence_in_range():
    score = compute_confidence(ConfidenceInputs(3, 1.0, 1.0, 0.0))
    assert 0.0 <= score <= 1.0
    assert score > 0.8


def test_more_evidence_increases_confidence():
    low = compute_confidence(ConfidenceInputs(0, 0.5, 0.5, 0.2))
    high = compute_confidence(ConfidenceInputs(3, 0.5, 0.5, 0.2))
    assert high > low


def test_ambiguity_penalty_reduces_confidence():
    clear = compute_confidence(ConfidenceInputs(2, 0.8, 1.0, 0.0))
    ambiguous = compute_confidence(ConfidenceInputs(2, 0.8, 1.0, 1.0))
    assert ambiguous < clear


def test_ungrounded_lowers_confidence():
    grounded = compute_confidence(ConfidenceInputs(1, 0.6, 1.0, 0.2))
    ungrounded = compute_confidence(ConfidenceInputs(1, 0.6, 0.0, 0.2))
    assert ungrounded < grounded


def test_degraded_confidence_is_capped():
    assert degraded_confidence(1.0) <= 0.4
    assert degraded_confidence(0.0) >= 0.0
