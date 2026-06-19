"""Sales pipeline analytics endpoint."""

from datetime import datetime

from fastapi import APIRouter, Depends

from backend import main as _main
from backend.models import PipelineAnalysisRequest
from backend.services.pipeline_analysis import analyze_pipeline

router = APIRouter()


@router.post("/pipeline/analyze")
async def pipeline_analysis_endpoint(
    payload: PipelineAnalysisRequest,
    current_user: dict = Depends(_main.get_current_user),
):
    opportunities = [op.model_dump() for op in payload.opportunities]
    results = analyze_pipeline(opportunities, payload.stage_probabilities)

    await _main.db.logs.insert_one(
        {
            "user": current_user["username"],
            "endpoint": "/pipeline/analyze",
            "action": "pipeline_analysis",
            "timestamp": datetime.utcnow(),
            "status": "success",
            "opportunities_count": len(opportunities),
        }
    )
    return results
