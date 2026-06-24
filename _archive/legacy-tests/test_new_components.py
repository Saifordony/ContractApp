"""Smoke tests for the new Dimension 2.2 visual components.

These exercise the pure HTML-building helpers so they can run without a live
Streamlit script context.
"""

from frontend.components.evidence_block import evidence_quote_html
from frontend.components.risk_heatmap import risk_heatmap_html, _count_statuses
from frontend.components.score_breakdown_bars import score_breakdown_bar_html
from frontend.components.onboarding_banner import onboarding_banner_html


def test_evidence_quote_html_includes_quote_and_location():
    html = evidence_quote_html("Either party may terminate with 30 days notice.", "section:Termination")
    assert "Either party may terminate" in html
    assert "section:Termination" in html
    assert "evidence-quote" in html


def test_risk_heatmap_counts_statuses():
    clauses = {
        "a": {"status": "found"},
        "b": {"status": "found"},
        "c": {"status": "partial"},
        "d": {"status": "missing"},
    }
    assert _count_statuses(clauses) == (2, 1, 1)
    html = risk_heatmap_html(clauses)
    assert "2 found" in html
    assert "1 partial" in html
    assert "1 missing" in html


def test_risk_heatmap_handles_empty():
    html = risk_heatmap_html({})
    assert "No clause status data" in html


def test_score_breakdown_bar_width_by_severity():
    high = score_breakdown_bar_html({"area": "Risk", "severity": "high"})
    low = score_breakdown_bar_html({"area": "Clarity", "severity": "low"})
    assert "width:80%" in high
    assert "#EF4444" in high  # danger
    assert "width:25%" in low
    assert "#22D68F" in low  # success


def test_onboarding_banner_html_has_four_steps():
    html = onboarding_banner_html()
    assert "1. Upload contract" in html
    assert "4. Benchmark & report" in html
