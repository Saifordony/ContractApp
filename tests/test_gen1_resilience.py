import pytest

pytest.importorskip("langchain_ollama")

import backend.gen1 as gen1


class _StubResp:
    def __init__(self, content):
        self.content = content


class _StubLLM:
    def __init__(self, outputs):
        self._outputs = list(outputs)

    def invoke(self, _prompt):
        if self._outputs:
            return _StubResp(self._outputs.pop(0))
        return _StubResp("{}")


def test_extract_json_payload_accepts_python_like_dict():
    payload = "{'approved': True, 'reasoning': 'ok',}"
    data = gen1._extract_json_payload(payload)
    assert data["approved"] is True
    assert data["reasoning"] == "ok"


def test_analyze_contract_sync_falls_back_when_llm_returns_non_json(monkeypatch):
    monkeypatch.setattr(gen1, "llm_model", _StubLLM(["not json at all"]))
    clauses = gen1.analyze_contract_sync(
        "This agreement includes payment terms and governing law in New York."
    )
    assert isinstance(clauses, dict)
    assert clauses


def test_evaluate_contract_sync_falls_back_to_rule_engine(monkeypatch):
    monkeypatch.setattr(gen1, "llm_model", _StubLLM(["invalid json output"]))
    result = gen1.evaluate_contract_sync({"payment_terms": "Net 30", "termination": "30 days notice"})
    assert "approved" in result
    assert "health_score" in result


def test_explain_clauses_falls_back_to_plain_language(monkeypatch):
    monkeypatch.setattr(gen1, "llm_model", _StubLLM(["no json here"]))
    explanations = gen1.explain_clauses_for_layman_sync({"payment_terms": "Client pays in 30 days."})
    assert "payment_terms" in explanations
    assert explanations["payment_terms"].startswith("This clause means:")
