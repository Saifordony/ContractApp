import importlib
import io
import sys
import types

from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def app_module(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "integration-secret")
    monkeypatch.setenv("BENCHMARK_ENABLED", "true")

    fake_gen1 = types.ModuleType("backend.gen1")

    async def _async_dict(*args, **kwargs):
        return {}

    async def _async_str(*args, **kwargs):
        return "ok"

    fake_gen1.analyze_contract = _async_dict
    fake_gen1.evaluate_contract = _async_dict
    fake_gen1.analyze_and_evaluate_contract = _async_dict
    fake_gen1.explain_clauses_for_layman = _async_dict
    fake_gen1.contract_chat = _async_str
    fake_gen1.extract_text_from_pdf_bytes = lambda *args, **kwargs: "sample text"
    fake_gen1.extract_text_from_upload_bytes = lambda *args, **kwargs: "sample text"
    fake_gen1.llm_model = None

    sys.modules["backend.gen1"] = fake_gen1
    sys.modules.pop("backend.main", None)

    module = importlib.import_module("backend.main")

    class _Logs:
        async def insert_one(self, doc):
            return None

    class _FakeDB:
        logs = _Logs()

    module.db = _FakeDB()

    async def _fake_current_user():
        return {"username": "admin"}

    module.app.dependency_overrides[module.get_current_user] = _fake_current_user
    return module


def test_benchmark_analyze_endpoint_returns_clause_results(app_module):
    client = TestClient(app_module.app)
    sample_text = (
        "EMPLOYMENT CONTRACT\n"
        "Payment Terms\n"
        "Employer shall pay salary within 30 days of invoice.\n"
        "Termination\n"
        "Either party may terminate with 30 days notice.\n"
        "Governing Law\n"
        "This contract is governed by Jordan law.\n"
    )

    response = client.post(
        "/benchmark/analyze",
        files={"file": ("sample.txt", sample_text.encode("utf-8"), "text/plain")},
        data={
            "contract_type": "employment",
            "jurisdiction": "jordan",
            "industry": "technology",
            "opt_in_store_user_data": "false",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "overall_score" in payload
    assert "clause_results" in payload
    assert payload["clause_results"]
