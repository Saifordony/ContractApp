"""Unit tests for the dependency-free helpers behind the multipage UI."""

import base64
import json
import time


def _make_jwt(exp: int) -> str:
    def seg(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    return f"{seg({'alg': 'HS256'})}.{seg({'sub': 'alice', 'exp': exp})}.sig"


def test_decode_jwt_exp_reads_claim():
    from frontend.auth import decode_jwt_exp, seconds_until_expiry

    exp = int(time.time()) + 600
    token = _make_jwt(exp)
    assert decode_jwt_exp(token) == exp
    remaining = seconds_until_expiry(token, now=time.time())
    assert 500 < remaining <= 600


def test_decode_jwt_exp_handles_garbage():
    from frontend.auth import decode_jwt_exp, seconds_until_expiry

    assert decode_jwt_exp("not-a-jwt") is None
    assert seconds_until_expiry("not-a-jwt") is None


def test_llm_status_indicator_states():
    from frontend.components.sidebar import llm_status_indicator

    assert "Ready" in llm_status_indicator({"reachable": True, "model": "llama3.1:8b", "available_models": ["llama3.1:8b"]})
    assert "Model loading" in llm_status_indicator({"reachable": True, "model": "llama3.1:8b", "available_models": []})
    assert "offline" in llm_status_indicator({"reachable": False})
    assert "offline" in llm_status_indicator(None)


def test_confidence_badge_html_thresholds():
    from frontend.components.ui import confidence_badge_html

    assert "confidence-high" in confidence_badge_html(0.9)
    assert "confidence-medium" in confidence_badge_html(0.5)
    assert "confidence-low" in confidence_badge_html(0.1)


def test_stat_card_html_renders_label_and_value():
    from frontend.components.ui import stat_card_html

    html = stat_card_html("Total Contracts", "12")
    assert "stat-card" in html
    assert "Total Contracts" in html
    assert "12" in html


def test_demo_data_is_consistent():
    from frontend.demo_data import DEMO_ANALYSIS_RESULTS, DEMO_CLIENT_NAME, DEMO_CONTRACT_TEXT

    assert DEMO_CLIENT_NAME == "Atlas Engineering LLC"
    assert "MASTER SERVICES AGREEMENT" in DEMO_CONTRACT_TEXT
    health = DEMO_ANALYSIS_RESULTS["health_evaluation"]
    assert 0 <= health["health_score"] <= 100
    # The flat clauses map only contains found clauses.
    assert "dispute_resolution" not in DEMO_ANALYSIS_RESULTS["clauses"]
    assert DEMO_ANALYSIS_RESULTS["structured_clauses"]["clauses"]["governing_law"]["status"] == "found"
