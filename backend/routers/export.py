"""Export router: real PDF, CSV, and JSON downloads of a contract's analysis."""
from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.database import get_database
from backend.dependencies import get_current_user
from backend.errors import not_found
from backend.services.audit import record_log
from backend.services.export_builders import build_csv_export, build_json_export
from backend.services.pdf_export import build_analysis_pdf

router = APIRouter(prefix="/contracts", tags=["export"])


async def _load(db: AsyncIOMotorDatabase, contract_id: str, owner: ObjectId) -> tuple[dict, dict, dict | None]:
    if not ObjectId.is_valid(contract_id):
        raise not_found("Contract")
    contract = await db.contracts.find_one({"_id": ObjectId(contract_id), "created_by": owner})
    if contract is None:
        raise not_found("Contract")
    analysis = await db.contract_analyses.find_one({"contract_id": contract["_id"]}, sort=[("created_at", -1)])
    if analysis is None:
        raise not_found("Analysis (run analysis before exporting)")
    benchmark = await db.benchmark_results.find_one({"contract_id": contract["_id"]}, sort=[("created_at", -1)])
    return contract, analysis, benchmark


def _attachment(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{contract_id}/export/pdf")
async def export_pdf(contract_id: str, current_user: dict = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_database)) -> Response:
    contract, analysis, benchmark = await _load(db, contract_id, current_user["_id"])
    pdf = build_analysis_pdf(contract, analysis, benchmark)
    await record_log(db, "export_generate", user_id=current_user["_id"],
                     resource_type="contract", resource_id=contract["_id"], metadata={"format": "pdf"})
    return _attachment(pdf, "application/pdf", f"analysis-{contract_id}.pdf")


@router.get("/{contract_id}/export/csv")
async def export_csv(contract_id: str, current_user: dict = Depends(get_current_user),
                     db: AsyncIOMotorDatabase = Depends(get_database)) -> Response:
    contract, analysis, _ = await _load(db, contract_id, current_user["_id"])
    csv_bytes = build_csv_export(contract, analysis, contract.get("language", "en"))
    await record_log(db, "export_generate", user_id=current_user["_id"],
                     resource_type="contract", resource_id=contract["_id"], metadata={"format": "csv"})
    return _attachment(csv_bytes, "text/csv", f"analysis-{contract_id}.csv")


@router.get("/{contract_id}/export/json")
async def export_json(contract_id: str, current_user: dict = Depends(get_current_user),
                      db: AsyncIOMotorDatabase = Depends(get_database)) -> Response:
    contract, analysis, benchmark = await _load(db, contract_id, current_user["_id"])
    json_bytes = build_json_export(contract, analysis, benchmark)
    await record_log(db, "export_generate", user_id=current_user["_id"],
                     resource_type="contract", resource_id=contract["_id"], metadata={"format": "json"})
    return _attachment(json_bytes, "application/json", f"analysis-{contract_id}.json")
