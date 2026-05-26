from backend.services.benchmark_baselines import REGIONAL_BASELINES, run_benchmark


def _long_text() -> str:
    return "This clause is fully detailed with obligations, timeframes, remedies, governing references, and clear implementation terms for all parties."


def test_full_coverage_employment_scores_100():
    clauses = {k: _long_text() for k in REGIONAL_BASELINES["employment"]["clauses"].keys()}
    result = run_benchmark(clauses, "employment")
    assert result["score"] == 100
    assert result["grade"] == "A"


def test_all_missing_scores_zero():
    result = run_benchmark({}, "employment")
    assert result["score"] == 0
    assert result["grade"] == "F"


def test_grade_boundaries():
    assert run_benchmark({}, "employment")["grade"] == "F"  # 0
    assert run_benchmark({"compensation": "x" * 100, "working_hours": "x" * 100, "leave_policy": "x" * 100}, "employment")["grade"] == "D"  # 40
    assert run_benchmark({"compensation": "x" * 100, "working_hours": "x" * 100, "leave_policy": "x" * 100, "probation": "x" * 100, "termination": "x" * 100}, "employment")["grade"] == "C"  # 55
    assert run_benchmark({"compensation": "x" * 100, "working_hours": "x" * 100, "leave_policy": "x" * 100, "probation": "x" * 100, "termination": "x" * 100, "confidentiality": "x" * 100}, "employment")["grade"] == "B"  # 67 -> wait
    assert run_benchmark({k: "x" * 100 for k in REGIONAL_BASELINES["employment"]["clauses"].keys()}, "employment")["grade"] == "A"


def test_partial_credit_for_thin_clause():
    result = run_benchmark({"compensation": "x" * 40}, "employment")
    comp = next(item for item in result["clause_breakdown"] if item["clause"] == "compensation")
    assert comp["earned"] == 10
    assert comp["status"] == "partial"


def test_unknown_contract_type_falls_back_to_general_commercial():
    result = run_benchmark({}, "unknown_type")
    assert result["contract_type"] == "general_commercial"


def test_employment_includes_market_comparison_when_salary_present():
    result = run_benchmark({"compensation": "Base salary is 5000 JOD per month with annual review and benefits package."}, "employment")
    assert "benchmark_comparisons" in result
    assert result["benchmark_comparisons"]
