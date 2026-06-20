"""Workspace stats — computed with server-side aggregation, never by pulling
documents into Python to average them.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.database import get_database
from backend.dependencies import get_current_user

router = APIRouter(prefix="/stats", tags=["stats"])

HIGH_RISK_THRESHOLD = 60


@router.get("/summary")
async def summary(current_user: dict = Depends(get_current_user),
                  db: AsyncIOMotorDatabase = Depends(get_database)) -> dict:
    owner = current_user["_id"]

    contracts_total = await db.contracts.count_documents({"created_by": owner})
    clients_total = await db.clients.count_documents({"created_by": owner})
    analyzed_total = await db.contracts.count_documents({"created_by": owner, "status": "analyzed"})

    # Reduce to the latest analysis per contract, then aggregate — all server-side.
    latest_per_contract = [
        {"$match": {"created_by": owner}},
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$contract_id",
            "score": {"$first": "$health.overall_score"},
            "needs_review": {"$first": "$needs_review_count"},
        }},
    ]

    rollup = await db.contract_analyses.aggregate(
        latest_per_contract + [{
            "$group": {
                "_id": None,
                "avg_health": {"$avg": "$score"},
                "outstanding": {"$sum": "$needs_review"},
            }
        }]
    ).to_list(length=1)
    avg_health = round(rollup[0]["avg_health"], 1) if rollup and rollup[0].get("avg_health") is not None else None
    outstanding_reviews = int(rollup[0]["outstanding"]) if rollup and rollup[0].get("outstanding") is not None else 0

    high_rows = await db.contract_analyses.aggregate(
        latest_per_contract
        + [{"$match": {"score": {"$lt": HIGH_RISK_THRESHOLD}}}, {"$sort": {"score": 1}}, {"$limit": 5}]
    ).to_list(length=5)
    high_ids = [r["_id"] for r in high_rows]
    titles: dict = {}
    if high_ids:
        async for contract in db.contracts.find({"_id": {"$in": high_ids}}, {"title": 1}):
            titles[contract["_id"]] = contract.get("title", "")
    high_risk = [
        {"contract_id": str(r["_id"]), "title": titles.get(r["_id"], ""), "score": r["score"]}
        for r in high_rows
    ]

    # Recent findings: a small, fixed number of latest analyses (bounded, not a scan).
    recent_docs = await db.contract_analyses.find(
        {"created_by": owner}).sort("created_at", -1).to_list(length=5)
    recent_ids = [d["contract_id"] for d in recent_docs]
    recent_titles: dict = {}
    if recent_ids:
        async for contract in db.contracts.find({"_id": {"$in": recent_ids}}, {"title": 1}):
            recent_titles[contract["_id"]] = contract.get("title", "")
    recent_findings = [{
        "contract_id": str(d["contract_id"]),
        "title": recent_titles.get(d["contract_id"], ""),
        "overall_score": d.get("health", {}).get("overall_score"),
        "degraded": d.get("degraded", False),
        "needs_review": d.get("needs_review_count", 0),
    } for d in recent_docs]

    return {
        "contracts_total": contracts_total,
        "clients_total": clients_total,
        "analyzed_total": analyzed_total,
        "avg_health_score": avg_health,
        "high_risk": high_risk,
        "recent_findings": recent_findings,
        "outstanding_reviews": outstanding_reviews,
    }
