from backend.services.contract_extraction_service import detect_document_type, extract_clauses_with_validation
from backend.services.contract_health import evaluate_contract_health_from_clauses
from backend.services.benchmark_baselines import run_benchmark
from backend.services.contract_intelligence import answer_contract_question


def test_document_type_detection_cv_content():
    text = "Experience with Git and agile methodologies. Skills: communication. Responsibilities and qualifications."
    result = detect_document_type(text)
    assert result["document_type"] == "cv_or_job_description"


def test_parties_validation_rejects_cv_noise():
    text = "Responsibilities include agile planning and Git workflows."
    result = extract_clauses_with_validation(text)
    parties = next((x for x in result["clause_results"] if x["clause_key"] == "parties"), None)
    assert parties is not None
    assert parties["status"] == "not_found"


def test_health_score_breakdown_exists():
    clauses = {"Compensation": "", "Termination": "Either party may terminate with notice."}
    result = evaluate_contract_health_from_clauses(clauses)
    assert "score_breakdown" in result
    assert "deductions" in result["score_breakdown"]


def test_benchmark_structure_contains_new_sections():
    result = run_benchmark({}, "employment")
    assert "benchmark_context" in result
    assert "clause_comparison" in result
    assert "priority_recommendations" in result


def test_chat_unrelated_greeting_message():
    result = answer_contract_question("This agreement is between A and B.", "hi")
    assert "contract" in result["answer"].lower() or result["not_found"]


def test_chat_contract_related_question():
    contract = "This agreement includes annual leave of 21 days and sick leave of 7 days."
    result = answer_contract_question(contract, "Does this contract mention vacation?")
    assert "answer" in result
