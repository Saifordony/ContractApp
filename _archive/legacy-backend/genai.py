"""GenAI contract analysis, evaluation, and stateless chat endpoints."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend import main as _main
from backend.models import ContractChatTextRequest, ContractTextAnalysisRequest
from backend.services.contract_chat_service import build_contract_chat_response
from backend.services.contract_analysis_service import (
    analyze_contract_text,
    analyze_uploaded_contract,
    build_health_evaluation,
    to_grounded_response,
    to_legacy_clause_response,
)

router = APIRouter()


@router.post("/genai/analyze-contract")
async def analyze_contract_endpoint(
    file: UploadFile = File(...),
    response_language: str = Form("english"),
    use_ocr: bool = Form(True),
    current_user: dict = Depends(_main.get_current_user),
):
    """Compatibility wrapper for Streamlit file analysis.

    Business logic lives in contract_analysis_service; this route only validates
    upload basics, logs, and adapts the canonical result to the legacy shape.
    """
    allowed_extensions = (".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg")
    if not file.filename or not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Supported files: PDF, DOCX, TXT, PNG, JPG, and JPEG")

    try:
        canonical = await analyze_uploaded_contract(
            await file.read(),
            file.filename,
            content_type=file.content_type,
            use_ocr=use_ocr,
            response_language=response_language,
        )
        await _main.db.logs.insert_one({
            "user": current_user["username"],
            "endpoint": "/genai/analyze-contract",
            "action": "contract_analysis",
            "timestamp": datetime.utcnow(),
            "status": "success",
            "analysis_source": canonical.get("analysis_source"),
            "degraded_mode": canonical.get("health_evaluation", {}).get("degraded_mode"),
        })
        return to_legacy_clause_response(canonical)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        await _main.db.logs.insert_one({
            "user": current_user["username"],
            "endpoint": "/genai/analyze-contract",
            "action": "contract_analysis",
            "timestamp": datetime.utcnow(),
            "status": "error",
            "error": exc.__class__.__name__,
        })
        print(f"/genai/analyze-contract failed: {exc}")
        raise HTTPException(status_code=500, detail="Contract analysis failed. Please try again.")


@router.post("/genai/analyze-contract-text")
async def analyze_contract_text_endpoint(
    payload: ContractTextAnalysisRequest,
    current_user: dict = Depends(_main.get_current_user),
):
    """Compatibility wrapper for Streamlit text analysis."""
    try:
        canonical = await analyze_contract_text(
            payload.contract_text,
            response_language=payload.response_language,
            include_clause_explanations=True,
        )
        await _main.db.logs.insert_one({
            "user": current_user["username"],
            "endpoint": "/genai/analyze-contract-text",
            "action": "contract_analysis",
            "timestamp": datetime.utcnow(),
            "status": "success",
            "analysis_source": canonical.get("analysis_source"),
            "degraded_mode": canonical.get("health_evaluation", {}).get("degraded_mode"),
        })
        return to_legacy_clause_response(canonical)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        await _main.db.logs.insert_one({
            "user": current_user["username"],
            "endpoint": "/genai/analyze-contract-text",
            "action": "contract_analysis",
            "timestamp": datetime.utcnow(),
            "status": "error",
            "error": exc.__class__.__name__,
        })
        print(f"/genai/analyze-contract-text failed: {exc}")
        raise HTTPException(status_code=500, detail="Contract analysis failed. Please try again.")


@router.post("/genai/evaluate-contract")
async def evaluate_contract_endpoint(
    payload: Dict[str, Any], current_user: dict = Depends(_main.get_current_user)
):
    """Compatibility wrapper around canonical health evaluation."""
    try:
        clauses = payload.get("clauses", payload)
        response_language = payload.get("response_language", "english")
        evaluation = await build_health_evaluation(clauses, response_language=response_language)
        await _main.db.logs.insert_one({
            "user": current_user["username"],
            "endpoint": "/genai/evaluate-contract",
            "action": "contract_health",
            "timestamp": datetime.utcnow(),
            "status": "success",
            "scoring_source": evaluation.get("scoring_source"),
            "degraded_mode": evaluation.get("degraded_mode"),
        })
        return evaluation
    except Exception as exc:
        await _main.db.logs.insert_one({
            "user": current_user["username"],
            "endpoint": "/genai/evaluate-contract",
            "action": "contract_health",
            "timestamp": datetime.utcnow(),
            "status": "error",
            "error": exc.__class__.__name__,
        })
        raise HTTPException(status_code=500, detail="Contract health evaluation failed. Please try again.")


@router.post("/genai/analyze")
async def grounded_analyze_endpoint(
    payload: ContractTextAnalysisRequest,
    current_user: dict = Depends(_main.get_current_user),
):
    """Primary grounded-analysis endpoint backed by contract_analysis_service."""
    try:
        canonical = await analyze_contract_text(
            payload.contract_text,
            response_language=payload.response_language,
            include_clause_explanations=False,
        )
        grounded = to_grounded_response(canonical)
        await _main.db.logs.insert_one({
            "user": current_user["username"],
            "endpoint": "/genai/analyze",
            "action": "contract_analysis",
            "timestamp": datetime.utcnow(),
            "status": "success",
            "degraded_mode": grounded.get("degraded_mode"),
            "overall_confidence": grounded.get("overall_confidence"),
        })
        return grounded
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        await _main.db.logs.insert_one({
            "user": current_user["username"],
            "endpoint": "/genai/analyze",
            "action": "contract_analysis",
            "timestamp": datetime.utcnow(),
            "status": "error",
            "error": exc.__class__.__name__,
        })
        print(f"/genai/analyze failed: {exc}")
        raise HTTPException(status_code=500, detail="Grounded analysis failed. Please try again.")


@router.post("/genai/contract-chat")
async def contract_chat_text_endpoint(
    request: ContractChatTextRequest, current_user: dict = Depends(_main.get_current_user)
):
    """Stateless contract chat that takes contract text directly in the request.

    Powers the multipage Chat page (which holds the contract in session rather
    than a saved record). Surfaces the answer with numeric confidence, evidence,
    risks, and suggested follow-ups from the chat service.
    """
    message = (request.message or request.question or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please enter a message for the contract assistant.")

    chat_history = [item.dict() for item in request.chat_history]
    return build_contract_chat_response(
        message=message,
        contract_text=request.contract_text or "",
        analysis_results=request.analysis_results or {},
        chat_history=chat_history,
        response_language=request.response_language,
        response_mode=request.response_mode,
        debug=request.debug,
    )
