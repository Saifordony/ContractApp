"""Benchmark service fallback implementations.

These lightweight implementations keep endpoints runnable in this repository layout.
"""

from typing import Any, Dict


def load_seed_from_repo() -> list[dict[str, Any]]:
    """Return an empty in-memory seed dataset when no bundled dataset is present."""
    return []


def ingest_seed_dataset(db: Any, seed_data: list[dict[str, Any]] | None = None) -> Dict[str, Any]:
    """No-op ingestion compatible response."""
    payload = seed_data if seed_data is not None else []
    return {"ingested": len(payload), "skipped": 0}


def run_benchmark_analysis(db: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deterministic placeholder benchmark response."""
    opportunities = payload.get("opportunities", []) if isinstance(payload, dict) else []
    return {
        "status": "benchmark_unavailable",
        "message": "Benchmark dataset/services are not configured in this lightweight repo layout.",
        "opportunities_count": len(opportunities),
    }
