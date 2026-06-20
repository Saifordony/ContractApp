"""Benchmark comparison and seed-data ingestion endpoints."""

import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend import main as _main
from backend.llm_config import llm_health_check
from backend.services.benchmark_orchestrator import analyze_uploaded_benchmark, compare_saved_contract
from backend.services.contract_analysis_service import normalize_analysis_results
from backend.services.benchmark_service import ingest_seed_dataset, load_seed_from_repo

router = APIRouter()


@router.post("/benchmark/compare/{contract_id}")
async def compare_contract_benchmark(contract_id: str, current_user: dict = Depends(_main.get_current_user)):
    _main.ensure_benchmark_enabled()
    object_id = _main.parse_object_id(contract_id, "contract ID")
    contract = await _main.db.contracts.find_one({"_id": object_id, "created_by": current_user["username"]})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    analysis = await _main.db.contract_analyses.find_one({"contract_id": contract_id}, sort=[("created_at", -1)])
    results = normalize_analysis_results((analysis or {}).get("results", {}))
    structured = results.get("structured_clauses", {}) if isinstance(results, dict) else {}
    validated_clauses = structured.get("clauses", {}) if isinstance(structured, dict) else {}
    if not validated_clauses:
        raise HTTPException(status_code=400, detail="Please analyze the contract before running benchmark comparison.")

    contract_type = (results.get("contract_type") if isinstance(results, dict) else None) or (results.get("health_evaluation", {}) if isinstance(results, dict) else {}).get("contract_type")
    readiness_review = results.get("health_evaluation", {}) if isinstance(results, dict) else {}
    ai_commentary_fn = _main.generate_benchmark_ai_commentary if llm_health_check().get("reachable") else None
    try:
        benchmark = compare_saved_contract(
            contract_id=contract_id,
            validated_clauses=validated_clauses,
            raw_contract_text=contract.get("content", ""),
            contract_type=contract_type,
            jurisdiction=readiness_review.get("jurisdiction") if isinstance(readiness_review, dict) else None,
            readiness_review=readiness_review,
            ai_commentary_fn=ai_commentary_fn,
        )
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Benchmark comparison failed. Please try again.") from exc

    await _main.db.contracts.update_one(
        {"_id": object_id},
        {"$set": {"benchmark_result": benchmark, "updated_at": datetime.utcnow()}},
    )
    await _main.db.logs.insert_one({
        "user": current_user["username"],
        "endpoint": f"/benchmark/compare/{contract_id}",
        "action": "benchmark_compare",
        "timestamp": datetime.utcnow(),
        "status": "success",
        "alignment_score": benchmark.get("overall_position", {}).get("alignment_score"),
    })
    return benchmark


@router.post("/benchmark/ingest")
async def ingest_benchmark_seed(
    payload: Dict[str, Any],
    current_user: dict = Depends(_main.get_current_user),
):
    _main.ensure_benchmark_enabled()

    allow_all = os.getenv("BENCHMARK_ALLOW_ALL_INGEST", "false").lower() == "true"
    if not allow_all and current_user["username"] not in {"admin", "dev"}:
        raise HTTPException(status_code=403, detail="Only admin/dev can ingest benchmark data")

    use_repo_seed = bool(payload.get("use_repo_seed", True))
    clear_first = bool(payload.get("clear_first", False))

    if use_repo_seed:
        result = load_seed_from_repo()
    else:
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise HTTPException(status_code=400, detail="items must be a list")
        result = ingest_seed_dataset(items, clear_first=clear_first)

    await _main.db.logs.insert_one(
        {
            "user": current_user["username"],
            "endpoint": "/benchmark/ingest",
            "action": "benchmark_ingest",
            "timestamp": datetime.utcnow(),
            "status": "success",
            "ingested": result.get("ingested", 0),
            "total": result.get("total", 0),
        }
    )
    return result


@router.post("/benchmark/analyze")
async def benchmark_analyze_endpoint(
    file: UploadFile = File(...),
    contract_type: str = Form(...),
    jurisdiction: str = Form(...),
    industry: Optional[str] = Form(None),
    opt_in_store_user_data: bool = Form(False),
    current_user: dict = Depends(_main.get_current_user),
):
    _main.ensure_benchmark_enabled()

    file_name = file.filename or "uploaded_contract.txt"
    if not file_name.lower().endswith((".pdf", ".docx", ".txt")):
        raise HTTPException(status_code=400, detail="Supported types: .pdf, .docx, .txt")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        result = analyze_uploaded_benchmark(
            filename=file_name,
            file_bytes=data,
            contract_type=contract_type,
            jurisdiction=jurisdiction,
            industry=industry,
            opt_in_store_user_data=opt_in_store_user_data,
        )

        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/benchmark/analyze",
                "action": "benchmark_analyze",
                "timestamp": datetime.utcnow(),
                "status": "success",
                "contract_type": contract_type,
                "jurisdiction": jurisdiction,
                "industry": industry,
                "overall_score": result.get("overall_score"),
            }
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/benchmark/analyze",
                "action": "benchmark_analyze",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(exc),
            }
        )
        raise HTTPException(status_code=500, detail="Benchmark comparison failed. Please try again.")
