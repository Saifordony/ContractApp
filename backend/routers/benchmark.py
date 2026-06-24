from fastapi import APIRouter, Depends
from backend.core.security import get_current_user
from backend.database import get_database
from backend.services.benchmark_service import benchmark_analysis, benchmark_contract
from backend.services.contract_service import get_contract

router = APIRouter(prefix="/benchmark", tags=["benchmark"])

@router.post("/compare/{contract_id}")
async def compare(contract_id: str, user=Depends(get_current_user)):
    db = get_database(); contract = await get_contract(db, user["id"], contract_id)
    latest = await db.analyses.find_one({"contract_id": contract_id, "owner_user_id": user["id"]}, sort=[("created_at", -1)])
    return await benchmark_contract(db, user["id"], contract, (latest or {}).get("analysis"))

@router.post("/analyze")
async def analyze(payload: dict, user=Depends(get_current_user)):
    return benchmark_analysis(payload.get("analysis", payload))
