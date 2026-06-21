from pathlib import Path


def test_chat_endpoint_uses_current_authenticated_contract_chat_service():
    source = Path("backend/routers/contracts.py").read_text()
    assert '@router.post("/{contract_id}/chat")' in source
    assert "user=Depends(get_current_user)" in source
    assert "chat_with_contract" in source
    assert "payload.question" in source
    assert "payload.explanation_language" in source


def test_chat_service_handles_unavailable_llm_with_degraded_fallback():
    source = Path("backend/services/chat_service.py").read_text()
    assert "if not health.get(\"reachable\")" in source
    assert "llm_unavailable=True" in source
    assert "used_contract" in source
    assert "response_language" in source
