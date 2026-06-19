from pathlib import Path


def _chat_endpoint_source() -> str:
    source = Path("backend/routers/contracts.py").read_text()
    start = source.index('@router.post("/contracts/{contract_id}/chat")')
    end = source.index('@router.post("/contracts/compare")', start)
    return source[start:end]


def test_chat_endpoint_classifies_before_requiring_contract_content():
    block = _chat_endpoint_source()
    assert "classify_chat_intent(message)" in block
    assert block.index("classify_chat_intent(message)") < block.index('if not contract.get("content")')
    assert "context_free_intents" in block


def test_chat_endpoint_does_not_gate_responses_on_llm_health():
    block = _chat_endpoint_source()
    assert "is_genai_configured()" not in block
    assert "llm_health_check()" not in block
