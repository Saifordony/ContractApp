import logging

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from io import BytesIO
from backend.core.security import get_current_user
from backend.database import get_database
from backend.services.analysis_service import analyze_contract_record
from backend.services.benchmark_service import benchmark_contract
from backend.services.chat_service import chat_with_contract
from backend.services.contract_service import get_contract, list_contracts, upload_contract, serialize_contract
from backend.services.report_service import generate_analysis_pdf
from pydantic import BaseModel

router = APIRouter(prefix="/contracts", tags=["contracts"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    question: str
    explanation_language: str = "en"

@router.get("")
async def contracts(user=Depends(get_current_user)):
    return await list_contracts(get_database(), user["id"])

@router.post("/upload")
async def upload(file: UploadFile = File(...), client_id: str | None = Form(None), name: str | None = Form(None), user=Depends(get_current_user)):
    return await upload_contract(get_database(), user["id"], file.filename or "contract.txt", await file.read(), client_id, name)

@router.get("/{contract_id}")
async def get_one(contract_id: str, user=Depends(get_current_user)):
    return serialize_contract(await get_contract(get_database(), user["id"], contract_id))

@router.post("/{contract_id}/analyze")
async def analyze(contract_id: str, explanation_language: str = "en", ui_language: str = "en", user=Depends(get_current_user)):
    logger.info("analysis route hit user_id=%s contract_id=%s", user["id"], contract_id)
    db = get_database()
    try:
        contract = await get_contract(db, user["id"], contract_id)
        logger.info("analysis contract found user_id=%s contract_id=%s", user["id"], contract_id)
        logger.info("analysis started user_id=%s contract_id=%s", user["id"], contract_id)
        result = await analyze_contract_record(db, contract, explanation_language=explanation_language, ui_language=ui_language)
        result["contract_id"] = contract_id
        result["extraction_metadata"] = contract.get("extraction_metadata", {})
        logger.info("analysis completed user_id=%s contract_id=%s degraded_mode=%s llm_used=%s", user["id"], contract_id, result.get("degraded_mode"), result.get("llm_used"))
        return result
    except HTTPException as exc:
        logger.warning("analysis failed user_id=%s contract_id=%s status=%s detail=%s", user["id"], contract_id, exc.status_code, exc.detail)
        raise
    except NameError as exc:
        logger.exception("analysis language helper error user_id=%s contract_id=%s explanation_language=%s ui_language=%s", user["id"], contract_id, explanation_language, ui_language)
        detail = "Arabic analysis failed due to a backend language helper error. English analysis still works." if explanation_language == "ar" else "Analysis failed due to a backend helper error."
        raise HTTPException(status_code=500, detail={"error_code": "ANALYSIS_LANGUAGE_HELPER_ERROR", "detail": detail, "explanation_language": explanation_language, "ui_language": ui_language}) from exc
    except Exception as exc:
        logger.exception("analysis unexpected error user_id=%s contract_id=%s explanation_language=%s ui_language=%s", user["id"], contract_id, explanation_language, ui_language)
        detail = "Analysis failed while generating Arabic explanation. Please check backend logs." if explanation_language == "ar" else "Analysis failed. Please try again or check system health."
        raise HTTPException(status_code=500, detail={"error_code": "ANALYSIS_FAILED", "detail": detail, "explanation_language": explanation_language, "ui_language": ui_language}) from exc


@router.get("/{contract_id}/analysis/report")
async def analysis_report(contract_id: str, report_language: str = "en", user=Depends(get_current_user)):
    db = get_database()
    contract = await get_contract(db, user["id"], contract_id)
    latest = await db.analyses.find_one({"contract_id": contract_id, "owner_user_id": user["id"]}, sort=[("created_at", -1)])
    if not latest or not latest.get("analysis"):
        raise HTTPException(status_code=400, detail="Run analysis before generating report.")
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    pdf = generate_analysis_pdf(contract, latest["analysis"], generated_at, language=report_language)
    safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in (contract.get("name") or "contract")).strip("-") or "contract"
    filename = f"contract-intelligence-report-{safe_name}-{datetime.utcnow().strftime('%Y%m%d')}.pdf"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(BytesIO(pdf), media_type="application/pdf", headers=headers)

@router.post("/{contract_id}/chat")
async def chat(contract_id: str, payload: ChatRequest, user=Depends(get_current_user)):
    contract = await get_contract(get_database(), user["id"], contract_id)
    return await chat_with_contract(get_database(), user["id"], contract, payload.question, explanation_language=payload.explanation_language)

@router.post("/{contract_id}/benchmark")
async def benchmark(contract_id: str, explanation_language: str = "en", user=Depends(get_current_user)):
    db = get_database(); contract = await get_contract(db, user["id"], contract_id)
    latest = await db.analyses.find_one({"contract_id": contract_id, "owner_user_id": user["id"]}, sort=[("created_at", -1)])
    return await benchmark_contract(db, user["id"], contract, (latest or {}).get("analysis"), explanation_language=explanation_language)

# Compatibility wrapper for legacy Streamlit flows.
@router.post("/{contract_id}/init-genai")
async def init_genai(contract_id: str, user=Depends(get_current_user)):
    contract = await get_contract(get_database(), user["id"], contract_id)
    return await analyze_contract_record(get_database(), contract)
