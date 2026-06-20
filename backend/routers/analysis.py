from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel
from backend.services.analysis_service import analyze_text, extract_text

router = APIRouter(prefix="/genai", tags=["compatibility-analysis"])

class TextPayload(BaseModel):
    contract_text: str | None = None
    text: str | None = None

@router.post("/analyze-contract")
async def analyze_contract(file: UploadFile = File(...)):
    text = extract_text(file.filename or "contract.txt", await file.read())
    return analyze_text(text)

@router.post("/analyze-contract-text")
async def analyze_contract_text(payload: TextPayload):
    return analyze_text(payload.contract_text or payload.text or "")

@router.post("/evaluate-contract")
async def evaluate_contract(payload: TextPayload):
    analysis = analyze_text(payload.contract_text or payload.text or "")
    return {k: analysis[k] for k in ["health_score", "risk_level", "missing_critical_clauses", "recommended_improvements", "source", "degraded_mode"]}

@router.post("/analyze")
async def analyze(payload: TextPayload):
    return analyze_text(payload.contract_text or payload.text or "")
