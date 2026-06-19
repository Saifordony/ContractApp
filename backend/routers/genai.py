"""GenAI contract analysis, evaluation, and stateless chat endpoints."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend import main as _main
from backend.gen1 import evaluate_contract, explain_clauses_for_layman, extract_text_from_upload_bytes
from backend.llm_config import is_genai_configured, llm_health_check
from backend.models import ContractChatTextRequest, ContractTextAnalysisRequest
from backend.services.contract_chat_service import build_contract_chat_response
from backend.services.contract_health import evaluate_contract_health_from_clauses
from backend.services.contract_intelligence import extract_key_clauses

router = APIRouter()


@router.post("/genai/analyze-contract")
async def analyze_contract_endpoint(
    file: UploadFile = File(...),
    response_language: str = Form("english"),
    use_ocr: bool = Form(True),
    current_user: dict = Depends(_main.get_current_user),
):
    allowed_extensions = (".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg")
    if not file.filename or not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Supported files: PDF, DOCX, TXT, PNG, JPG, and JPEG")

    if not is_genai_configured():
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: Ollama not configured",
        )

    analysis_health = None
    try:
        file_bytes = await file.read()
        extracted = extract_text_from_upload_bytes(
            file_bytes,
            file.filename,
            content_type=file.content_type,
            use_ocr=use_ocr,
            response_language=response_language,
        )
        contract_text = extracted["text"]
        analysis_health = _main.log_analysis_llm_context("/genai/analyze-contract")
        structured_clauses = extract_key_clauses(contract_text)
        found_clauses = {
            k: v.get("extracted_text")
            for k, v in structured_clauses.get("clauses", {}).items()
            if isinstance(v, dict) and v.get("status") == "found" and v.get("extracted_text")
        }
        clause_explanations = (
            await explain_clauses_for_layman(found_clauses, response_language=response_language)
            if found_clauses
            else {}
        )

        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/analyze-contract",
                "action": "contract_analysis",
                "timestamp": datetime.utcnow(),
                "status": "success",
            }
        )

        ocr_warning = None
        if extracted.get("used_ocr") and extracted.get("ocr_confidence") is not None and extracted.get("ocr_confidence", 1) < 0.45:
            ocr_warning = "جودة المسح منخفضة، لذلك قد يكون بعض النص المستخرج غير دقيق." if response_language.lower().startswith("ar") else "The scan quality is low, so some extracted text may be inaccurate."
        return {
            "structured_clauses": structured_clauses,
            "clause_explanations": clause_explanations,
            "contract_text": contract_text,
            "used_ocr": bool(extracted.get("used_ocr")),
            "ocr_confidence": extracted.get("ocr_confidence"),
            "ocr_warning": ocr_warning,
        }
    except HTTPException:
        raise
    except Exception as e:
        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/analyze-contract",
                "action": "contract_analysis",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(e),
            }
        )
        print(f"/genai/analyze-contract failed: {e}")
        raise HTTPException(status_code=500, detail=_main.format_analysis_error(e, analysis_health))


@router.post("/genai/analyze-contract-text")
async def analyze_contract_text_endpoint(
    payload: ContractTextAnalysisRequest,
    current_user: dict = Depends(_main.get_current_user),
):
    if not is_genai_configured():
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: Ollama not configured",
        )

    contract_text = (payload.contract_text or "").strip()
    if len(contract_text) < 100:
        raise HTTPException(status_code=422, detail="Contract text is too short to analyze.")

    analysis_health = None
    try:
        analysis_health = _main.log_analysis_llm_context("/genai/analyze-contract-text")
        structured_clauses = extract_key_clauses(contract_text)
        found_clauses = {
            k: v.get("extracted_text")
            for k, v in structured_clauses.get("clauses", {}).items()
            if isinstance(v, dict) and v.get("status") == "found" and v.get("extracted_text")
        }
        clause_explanations = (
            await explain_clauses_for_layman(found_clauses, response_language=payload.response_language)
            if found_clauses
            else {}
        )

        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/analyze-contract-text",
                "action": "contract_analysis_text",
                "timestamp": datetime.utcnow(),
                "status": "success",
                "chunk_count": structured_clauses.get("chunk_count", 0),
                "conflicts_count": len(structured_clauses.get("conflicts", [])),
            }
        )
        return {
            "structured_clauses": structured_clauses,
            "clause_explanations": clause_explanations,
        }
    except HTTPException:
        raise
    except Exception as e:
        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/analyze-contract-text",
                "action": "contract_analysis_text",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(e),
            }
        )
        print(f"/genai/analyze-contract-text failed: {e}")
        raise HTTPException(status_code=500, detail=_main.format_analysis_error(e, analysis_health))


@router.post("/genai/evaluate-contract")
async def evaluate_contract_endpoint(
    payload: Dict[str, Any], current_user: dict = Depends(_main.get_current_user)
):
    if not is_genai_configured():
        raise HTTPException(
            status_code=503,
            detail="GenAI service unavailable: Ollama not configured",
        )

    try:
        clauses = payload.get("clauses", payload)
        response_language = payload.get("response_language", "english")

        llm_evaluation = await evaluate_contract(
            clauses,
            response_language=response_language,
        )
        rule_evaluation = evaluate_contract_health_from_clauses(clauses, response_language=response_language)

        evaluation = {
            **llm_evaluation,
            **rule_evaluation,
            "llm_assessment": llm_evaluation,
            "module": "contract_health",
        }

        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/evaluate-contract",
                "action": "contract_evaluation",
                "timestamp": datetime.utcnow(),
                "status": "success",
            }
        )

        return evaluation
    except HTTPException:
        raise
    except Exception as e:
        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": "/genai/evaluate-contract",
                "action": "contract_evaluation",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(e),
            }
        )
        raise HTTPException(status_code=500, detail=_main.format_analysis_error(e, llm_health_check()))


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
