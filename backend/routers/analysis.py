from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from backend.core.security import get_current_user
from backend.services.analysis_service import analyze_text, extract_text

router = APIRouter(prefix="/genai", tags=["compatibility-analysis"])

class TextPayload(BaseModel):
    contract_text: str | None = None
    text: str | None = None

@router.post("/analyze-contract")
async def analyze_contract(file: UploadFile = File(...), user=Depends(get_current_user)):
    text = extract_text(file.filename or "contract.txt", await file.read())
    return analyze_text(text)

@router.post("/analyze-contract-text")
async def analyze_contract_text(payload: TextPayload, user=Depends(get_current_user)):
    return analyze_text(payload.contract_text or payload.text or "")

@router.post("/evaluate-contract")
async def evaluate_contract(payload: TextPayload, user=Depends(get_current_user)):
    analysis = analyze_text(payload.contract_text or payload.text or "")
    return {k: analysis[k] for k in ["health_score", "risk_level", "missing_critical_clauses", "recommended_improvements", "source", "degraded_mode"]}

@router.post("/analyze")
async def analyze(payload: TextPayload, user=Depends(get_current_user)):
    return analyze_text(payload.contract_text or payload.text or "")
