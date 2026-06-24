from datetime import datetime, timezone
import os
import platform
import sys
from pathlib import Path

import fastapi
from fastapi import APIRouter, Depends

from backend import database
from backend.config import get_settings
from backend.core.security import get_current_user
from backend.services.llm_service import llm_debug_status, llm_health, test_llm_model

router = APIRouter(tags=["health"])


def _secret_configured(value: str | None) -> bool:
    return bool(value and value != "dev-secret-key-change-me")


@router.get("/healthz")
async def healthz():
    settings = get_settings()
    mongo = "unknown"
    try:
        if database.db is not None:
            await database.db.command("ping")
            mongo = "connected"
        else:
            mongo = "not_connected"
    except Exception:
        mongo = "unreachable"
    llm = llm_health()
    return {
        "Active Backend": settings.active_backend,
        "Active Backend File": settings.active_backend_file,
        "Backend Build": settings.backend_build,
        "mongodb_status": mongo,
        "auth_status": "enabled",
        "llm_ollama_status": "reachable" if llm.get("reachable") else "unreachable",
        "llm_reachable": bool(llm.get("reachable")),
        "ollama_url": settings.ollama_base_url,
        "active_model": settings.ollama_model,
        "last_llm_error": llm.get("error") or llm.get("technical_error"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/llm/health")
def llm_status():
    return llm_health()


@router.post("/llm/test")
def llm_test(user=Depends(get_current_user)):
    return test_llm_model()


@router.get("/system/diagnostics")
async def system_diagnostics(user=Depends(get_current_user)):
    settings = get_settings()
    db = database.get_database()
    upload_probe = Path("/tmp/contractapp-upload-probe")
    upload_writable = False
    try:
        upload_probe.write_text("ok")
        upload_probe.unlink(missing_ok=True)
        upload_writable = True
    except Exception:
        upload_writable = False
    counts = {
        "clients": await db.clients.count_documents({"owner_user_id": user["id"]}),
        "contracts": await db.contracts.count_documents({"owner_user_id": user["id"]}),
        "analyses": await db.analyses.count_documents({"owner_user_id": user["id"]}),
        "chat_sessions": await db.chat_sessions.count_documents({"owner_user_id": user["id"]}),
        "benchmarks": await db.benchmarks.count_documents({"owner_user_id": user["id"]}),
    }
    # User count is intentionally scoped to the authenticated user to avoid leaking tenant-wide totals.
    counts["users"] = 1
    return {
        "python_version": sys.version.split()[0],
        "fastapi_version": fastapi.__version__,
        "platform": platform.platform(),
        "docker_mode_detected": os.path.exists("/.dockerenv"),
        "api_internal_url": os.getenv("API_BASE_URL", "http://backend:8000"),
        "browser_backend_url": "http://localhost:8000",
        "docker_url_explanation": "The Streamlit container uses the internal Docker URL to reach FastAPI. Your browser uses localhost.",
        "collection_counts": counts,
        "config_checks": {
            "jwt_secret_configured": _secret_configured(settings.jwt_secret),
            "mongodb_url_configured": bool(settings.mongodb_url),
            "ollama_url_configured": bool(settings.ollama_base_url),
            "active_model_configured": bool(settings.ollama_model),
            "upload_directory_writable": upload_writable,
        },
        "llm_debug": llm_debug_status(),
        "recent_safe_errors": {
            "last_backend_error": None,
            "last_llm_error": llm_health().get("error"),
            "last_upload_error": None,
            "last_analysis_error": llm_debug_status().get("last_parser_error"),
            "last_chat_error": None,
            "last_benchmark_error": None,
        },
    }
