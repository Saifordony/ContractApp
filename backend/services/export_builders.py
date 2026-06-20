"""CSV and JSON export builders (UTF-8, fully bilingual)."""
from __future__ import annotations

import csv
import io
import json

from backend.constants import CLAUSE_LABELS


def build_json_export(contract: dict, analysis: dict, benchmark: dict | None) -> bytes:
    payload = {
        "contract": {
            "id": str(contract["_id"]),
            "title": contract.get("title"),
            "contract_type": contract.get("contract_type"),
            "region": contract.get("region"),
            "language": contract.get("language"),
        },
        "analysis": _public_analysis(analysis),
        "benchmark": _public_benchmark(benchmark) if benchmark else None,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def build_csv_export(contract: dict, analysis: dict, language: str = "en") -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "key", "label", "status_or_score", "confidence", "detail", "evidence"])

    for clause in analysis.get("clauses", []):
        label = CLAUSE_LABELS.get(clause["key"], {}).get(language, clause["key"])
        evidence = clause["evidence"][0]["text"] if clause.get("evidence") else ""
        writer.writerow([
            "clause", clause["key"], label, clause.get("status", ""),
            round(clause.get("confidence", 0), 3), clause.get("explanation", ""), evidence,
        ])

    health = analysis.get("health", {})
    for dim in health.get("dimensions", []):
        writer.writerow(["dimension", dim["key"], dim["key"], dim.get("score", 0), "", dim.get("explanation", ""), ""])
    writer.writerow(["health", "overall", "overall_score", health.get("overall_score", 0),
                     round(health.get("confidence", 0), 3), f"grade {health.get('grade', '-')}", ""])

    return output.getvalue().encode("utf-8")


def _public_analysis(analysis: dict) -> dict:
    return {
        "language": analysis.get("language"),
        "degraded": analysis.get("degraded"),
        "model": analysis.get("model"),
        "confidence": analysis.get("confidence"),
        "clauses": analysis.get("clauses"),
        "health": analysis.get("health"),
        "created_at": analysis.get("created_at"),
    }


def _public_benchmark(benchmark: dict) -> dict:
    return {
        "contract_type": benchmark.get("contract_type"),
        "region": benchmark.get("region"),
        "overall_score": benchmark.get("overall_score"),
        "grade": benchmark.get("grade"),
        "degraded": benchmark.get("degraded"),
        "confidence": benchmark.get("confidence"),
        "gaps": benchmark.get("gaps"),
        "created_at": benchmark.get("created_at"),
    }
