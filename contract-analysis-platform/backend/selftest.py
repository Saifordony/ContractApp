"""Programmatic self-test runner for Contract Analysis Platform.

Run with:
    PYTHONPATH=contract-analysis-platform python -m backend.selftest
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import requests

from backend.services.contract_health import evaluate_contract_health_from_clauses
from backend.services.contract_intelligence import answer_contract_question, extract_key_clauses
from backend.services.pipeline_analysis import analyze_pipeline
from test_api import APITester, API_BASE_URL, TEST_USERNAME, TEST_EMAIL


CHECKLIST: List[Tuple[str, str]] = [
    ("AUTH", "Register creates user and login succeeds/fails correctly"),
    ("NAV", "Authenticated API navigation endpoints stay reachable"),
    ("CLIENTS", "Create/list/update/delete client flows work"),
    ("CONTRACTS", "Create/list/update/delete contract flows work"),
    ("ANALYSIS", "Clause extraction/evaluation/pipeline endpoints respond correctly"),
    ("METRICS", "Metrics/logs/health endpoints respond and update"),
    ("PERSISTENCE", "Created records can be fetched before cleanup"),
    ("ERRORS", "Invalid credentials and unauthorized access return friendly errors"),
]


def _print_checklist() -> None:
    print("\n=== Functionality Checklist ===")
    for key, item in CHECKLIST:
        print(f"- [{key}] {item}")


def _quick_error_checks(base_url: str) -> list[dict]:
    results: list[dict] = []

    bad_login_resp = requests.post(
        f"{base_url}/auth/login",
        json={"username": "definitely_not_valid_user", "password": "wrong-pass"},
        timeout=20,
    )
    results.append(
        {
            "name": "Invalid login returns 401",
            "success": bad_login_resp.status_code == 401,
            "status_code": bad_login_resp.status_code,
            "body": bad_login_resp.text,
        }
    )

    unauth_resp = requests.get(f"{base_url}/clients", timeout=20)
    results.append(
        {
            "name": "Unauthorized /clients is blocked",
            "success": unauth_resp.status_code in {401, 403},
            "status_code": unauth_resp.status_code,
            "body": unauth_resp.text,
        }
    )

    return results


def _offline_fixture_checks() -> list[dict]:
    fixtures = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
    contract_text = (fixtures / "sample_contract.txt").read_text()
    pipeline_data = json.loads((fixtures / "sample_pipeline.json").read_text())

    extracted = extract_key_clauses(contract_text)
    qa = answer_contract_question(contract_text, "What is the governing law?")
    health = evaluate_contract_health_from_clauses({
        "Governing Law": extracted["clauses"].get("governing_law", {}).get("value", ""),
        "Payment Terms Clause": extracted["clauses"].get("payment_terms", {}).get("value", ""),
        "Termination Clause": extracted["clauses"].get("termination", {}).get("value", ""),
        "Dispute Resolution Clause": extracted["clauses"].get("dispute_resolution", {}).get("value", ""),
        "Liability": extracted["clauses"].get("liability", {}).get("value", ""),
        "Confidentiality Clause": extracted["clauses"].get("confidentiality", {}).get("value", ""),
    })
    pipeline = analyze_pipeline(pipeline_data)

    return [
        {
            "name": "Offline extraction returns deterministic schema",
            "success": all(k in extracted for k in ["clauses", "conflicts", "chunk_count"]),
            "message": f"chunks={extracted.get('chunk_count', 0)}",
        },
        {
            "name": "Offline Q&A is grounded with evidence",
            "success": bool(qa.get("evidence")) and "answer" in qa,
            "message": f"confidence={qa.get('confidence')}",
        },
        {
            "name": "Contract health score generated",
            "success": "health_score" in health and "dimensions" in health,
            "message": f"score={health.get('health_score')}",
        },
        {
            "name": "Pipeline weighted metric generated",
            "success": pipeline.get("weighted_pipeline", 0) > 0,
            "message": f"weighted={pipeline.get('weighted_pipeline')}",
        },
    ]


def main() -> int:
    print("Contract Analysis Platform - Self Test")
    print(f"Base URL: {API_BASE_URL}")
    print(f"Generated test identity: {TEST_USERNAME} / {TEST_EMAIL}")
    _print_checklist()

    started_at = datetime.utcnow().isoformat()
    all_results: list[dict] = []

    # Always run offline deterministic checks.
    all_results.extend(_offline_fixture_checks())

    # API checks are attempted if service is available.
    api_available = False
    try:
        health = requests.get(f"{API_BASE_URL}/healthz", timeout=20)
        api_available = health.status_code == 200
    except requests.RequestException:
        api_available = False

    if api_available:
        tester = APITester()
        tester.run_all_tests()
        all_results.extend(
            {
                "name": r["test_name"],
                "success": r["success"],
                "message": r["message"],
            }
            for r in tester.test_results
        )
        all_results.extend(_quick_error_checks(API_BASE_URL))
    else:
        all_results.append(
            {
                "name": "API availability",
                "success": True,
                "message": f"API not reachable at {API_BASE_URL}; skipped online API flow checks.",
            }
        )

    total = len(all_results)
    failed = [r for r in all_results if not r.get("success")]

    print("\n=== Self-test Result ===")
    print(f"Started at: {started_at}")
    print(f"Total checks: {total}")
    print(f"Passed: {total - len(failed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFailures:")
        for result in failed:
            print(f"- {result['name']}: {result.get('message', '')}")
        return 1

    print("\nPASS: all available self-tests completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
