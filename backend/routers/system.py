"""Health checks, request logs, and usage metrics."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend import main as _main
from backend.llm_config import llm_health_check

router = APIRouter()


@router.get("/logs")
async def get_logs(
    user: Optional[str] = Query(None),
    endpoint: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(_main.get_current_user),
):
    filter_dict = {}
    if user:
        filter_dict["user"] = user
    if endpoint:
        filter_dict["endpoint"] = endpoint
    if status:
        filter_dict["status"] = status
    if level:
        filter_dict["level"] = level

    skip = (page - 1) * limit
    logs = await _main.db.logs.find(filter_dict).skip(skip).limit(limit).to_list(limit)
    total = await _main.db.logs.count_documents(filter_dict)

    for log in logs:
        log["_id"] = str(log["_id"])

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/metrics")
async def get_metrics(current_user: dict = Depends(_main.get_current_user)):
    total_requests = await _main.db.logs.count_documents({})
    successful_requests = await _main.db.logs.count_documents({"status": "success"})
    failed_requests = await _main.db.logs.count_documents({"status": "error"})

    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "success_rate": (
            (successful_requests / total_requests * 100) if total_requests > 0 else 0
        ),
    }


@router.get("/metrics/chat-quality")
async def get_chat_quality_metrics(current_user: dict = Depends(_main.get_current_user)):
    user_filter = {"user": current_user["username"], "action": "contract_chat", "status": "success"}
    total = await _main.db.logs.count_documents(user_filter)
    low_confidence = await _main.db.logs.count_documents({**user_filter, "confidence": {"$lt": 0.35}})
    out_of_scope = await _main.db.logs.count_documents({**user_filter, "intent": "out_of_scope"})
    no_evidence = await _main.db.logs.count_documents({**user_filter, "evidence_count": 0})

    return {
        "total_chat_requests": total,
        "low_confidence_rate": (low_confidence / total * 100) if total else 0,
        "out_of_scope_rate": (out_of_scope / total * 100) if total else 0,
        "no_evidence_rate": (no_evidence / total * 100) if total else 0,
    }


@router.get("/healthz")
async def health_check():
    mongo_ok = "connected"
    try:
        await _main.db_client.admin.command("ping")
    except Exception:
        mongo_ok = "unreachable"
    return {
        "status": "ok",
        "build": _main.APP_BUILD,
        "mongodb": mongo_ok,
        "llm": llm_health_check(),
    }


@router.get("/llm/health")
async def llm_health():
    return llm_health_check()


@router.get("/readyz")
async def readiness_check():
    try:
        await _main.db_client.admin.command("ping")
        return {"status": "ready", "timestamp": datetime.utcnow()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")
