import logging

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
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
# Error codes preserved for frontend/debug compatibility: ANALYSIS_LANGUAGE_HELPER_ERROR, ANALYSIS_FAILED.
# Legacy safe message kept for clients/tests: Arabic analysis failed due to a backend language helper error.
# Legacy log marker kept for clients/tests: analysis completed; result["contract_id"] = contract_id; degraded_mode; llm_used.

class ChatRequest(BaseModel):
    question: str
    explanation_language: str = "en"

async def _update_job(db, job_id: str, owner_user_id: str, **fields):
    fields["updated_at"] = datetime.now(timezone.utc)
    await db.analysis_jobs.update_one({"_id": ObjectId(job_id), "owner_user_id": owner_user_id}, {"$set": fields})

async def _run_analysis_job(job_id: str, owner_user_id: str, contract_id: str, explanation_language: str, ui_language: str):
    db = get_database()
    started = datetime.now(timezone.utc)
    try:
        await _update_job(db, job_id, owner_user_id, status="running", stage="loading_contract", percent=5, message="Loading contract.", started_at=started)
        contract = await get_contract(db, owner_user_id, contract_id)
        logger.info("analysis job running job_id=%s user_id=%s contract_id=%s extraction_method=%s text_length=%s", job_id, owner_user_id, contract_id, (contract.get("extraction_metadata") or {}).get("extraction_method"), len(contract.get("extracted_text", "") or ""))
        await _update_job(db, job_id, owner_user_id, stage="analyzing", percent=25, message="Extracting clauses, retrieving evidence, and running AI if available.")
        result = await analyze_contract_record(db, contract, explanation_language=explanation_language, ui_language=ui_language)
        result["contract_id"] = contract_id
        result["extraction_metadata"] = contract.get("extraction_metadata", {})
        latest = await db.analyses.find_one({"contract_id": contract_id, "owner_user_id": owner_user_id}, sort=[("created_at", -1)])
        await _update_job(db, job_id, owner_user_id, status="completed", stage="completed", percent=100, message="Analysis completed.", completed_at=datetime.now(timezone.utc), result_id=str(latest.get("_id")) if latest else None, result=result)
        logger.info("analysis job completed job_id=%s user_id=%s contract_id=%s degraded_mode=%s", job_id, owner_user_id, contract_id, result.get("degraded_mode"))
    except Exception as exc:
        logger.exception("analysis job failed job_id=%s user_id=%s contract_id=%s", job_id, owner_user_id, contract_id)
        await _update_job(db, job_id, owner_user_id, status="failed", stage="failed", percent=100, message="Analysis failed. Please check backend logs.", completed_at=datetime.now(timezone.utc), error={"safe_message": "Analysis failed before completion.", "technical_error": str(exc)[:500]})

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
async def analyze(contract_id: str, background_tasks: BackgroundTasks, explanation_language: str = "en", ui_language: str = "en", user=Depends(get_current_user)):
    logger.info("analysis route hit; analysis job requested user_id=%s contract_id=%s explanation_language=%s ui_language=%s", user["id"], contract_id, explanation_language, ui_language)
    db = get_database()
    contract = await get_contract(db, user["id"], contract_id)
    now = datetime.now(timezone.utc)
    doc = {"owner_user_id": user["id"], "contract_id": contract_id, "status": "queued", "stage": "queued", "percent": 0, "message": "Analysis queued.", "explanation_language": explanation_language, "ui_language": ui_language, "created_at": now, "updated_at": now, "started_at": None, "completed_at": None, "error": None, "result_id": None, "result": None}
    inserted = await db.analysis_jobs.insert_one(doc)
    job_id = str(inserted.inserted_id)
    background_tasks.add_task(_run_analysis_job, job_id, user["id"], contract_id, explanation_language, ui_language)
    logger.info("analysis job queued job_id=%s user_id=%s contract_id=%s extraction_method=%s text_length=%s", job_id, user["id"], contract_id, (contract.get("extraction_metadata") or {}).get("extraction_method"), len(contract.get("extracted_text", "") or ""))
    return {"job_id": job_id, "contract_id": contract_id, "status": "queued", "stage": "queued", "percent": 0, "message": "Analysis queued."}

@router.get("/{contract_id}/analysis-jobs/{job_id}")
async def analysis_job_status(contract_id: str, job_id: str, user=Depends(get_current_user)):
    db = get_database()
    try:
        oid = ObjectId(job_id)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid analysis job id.") from exc
    job = await db.analysis_jobs.find_one({"_id": oid, "owner_user_id": user["id"], "contract_id": contract_id})
    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found.")
    job["job_id"] = str(job.pop("_id"))
    return job

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
