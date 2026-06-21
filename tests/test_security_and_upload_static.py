from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_contract_processing_compatibility_endpoints_require_auth():
    analysis = read("backend/routers/analysis.py")
    chat = read("backend/routers/chat.py")
    benchmark = read("backend/routers/benchmark.py")
    health = read("backend/routers/health.py")
    assert "get_current_user" in analysis
    assert "user=Depends(get_current_user)" in analysis
    assert "get_current_user" in chat and "user=Depends(get_current_user)" in chat
    assert '@router.post("/analyze")' in benchmark and "user=Depends(get_current_user)" in benchmark
    assert '@router.post("/llm/test")' in health and "user=Depends(get_current_user)" in health


def test_upload_validation_and_ocr_extraction_are_active():
    contract_service = read("backend/services/contract_service.py")
    analysis = read("backend/services/analysis_service.py")
    assert "MAX_UPLOAD_BYTES = 20 * 1024 * 1024" in contract_service
    assert "SUPPORTED_EXTENSIONS" in contract_service
    assert "Unsupported file type" in contract_service
    assert "extract_contract_text" in contract_service
    for token in ["OCR_MAX_PAGES", "pytesseract", "ara+eng", "eng+ara", "get_pixmap", "extraction_method"]:
        assert token in analysis


def test_stale_legacy_tests_are_archived_not_active():
    assert (ROOT / "_archive/legacy-tests/test_contract_chat_service.py").exists()
    stale_imports = [
        "from backend.services.contract_chat_service",
        "from backend.services.contract_health",
        "from backend.services.contract_intelligence",
        "from backend.services.grounded_analysis",
        "from frontend.components.health_ring",
    ]
    active_tests = "\n".join(path.read_text(errors="ignore") for path in (ROOT / "tests").glob("test_*.py") if path.name != "test_security_and_upload_static.py")
    for missing_import in stale_imports:
        assert missing_import not in active_tests
