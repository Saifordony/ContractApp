"""Programmatic self-test runner for Contract Analysis Platform.

Run with:
    PYTHONPATH=contract-analysis-platform python -m backend.selftest
"""

from __future__ import annotations

import requests
from datetime import datetime
from typing import List, Tuple

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

    # Invalid login should fail with 401.
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

    # Unauthorized protected endpoint should fail with 403/401.
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


def main() -> int:
    print("Contract Analysis Platform - Self Test")
    print(f"Base URL: {API_BASE_URL}")
    print(f"Generated test identity: {TEST_USERNAME} / {TEST_EMAIL}")
    _print_checklist()

    try:
        health = requests.get(f"{API_BASE_URL}/healthz", timeout=20)
        if health.status_code != 200:
            print(f"\nFAIL: health check returned status {health.status_code}")
            return 1
    except requests.RequestException as exc:
        print(f"\nFAIL: cannot reach API at {API_BASE_URL}: {exc}")
        return 1

    tester = APITester()
    started_at = datetime.utcnow().isoformat()
    tester.run_all_tests()

    extra_results = _quick_error_checks(API_BASE_URL)
    tester.test_results.extend(
        {
            "test_name": r["name"],
            "success": r["success"],
            "message": f"status={r['status_code']}",
            "response_data": r["body"],
            "timestamp": datetime.utcnow().isoformat(),
        }
        for r in extra_results
    )

    total = len(tester.test_results)
    passed = sum(1 for r in tester.test_results if r["success"])
    failed = total - passed

    print("\n=== Self-test Result ===")
    print(f"Started at: {started_at}")
    print(f"Total checks: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed:
        print("\nFailures:")
        for result in tester.test_results:
            if not result["success"]:
                print(f"- {result['test_name']}: {result['message']}")
        return 1

    print("\nPASS: all automated self-tests completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
