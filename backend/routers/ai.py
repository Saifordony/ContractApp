"""AI router: the single grounded pipeline exposed over streaming (SSE) endpoints,
plus read endpoints for stored analysis, chat history, and benchmark results.
"""
from __future__ import annotations

import asyncio
import json

from bson import ObjectId
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.database import get_database
from backend.dependencies import get_current_user
from backend.errors import not_found
from backend.models.analysis import AnalysisOut
from backend.models.benchmark import BenchmarkOut
from backend.models.chat import ChatMessageOut, ChatRequest
from backend.models.common import utcnow
from backend.services.ai_pipeline import analyze_contract, answer_question_stream
from backend.services.audit import record_log
from backend.services.benchmark import compare_to_standard, find_standard

router = APIRouter(prefix="/contracts", tags=["ai"])

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _owned_contract(db: AsyncIOMotorDatabase, contract_id: str, owner: ObjectId) -> dict:
    if not ObjectId.is_valid(contract_id):
        raise not_found("Contract")
    doc = await db.contracts.find_one({"_id": ObjectId(contract_id), "created_by": owner})
    if doc is None:
        raise not_found("Contract")
    return doc


def _analysis_doc(contract: dict, result: dict) -> dict:
    needs_review = sum(1 for c in result["clauses"] if c["status"] in ("needs_review", "not_found"))
    return {
        "contract_id": contract["_id"],
        "created_by": contract["created_by"],
        "language": result["language"],
        "degraded": result["degraded"],
        "model": result["model"],
        "confidence": float(result["confidence"]),
        "clauses": result["clauses"],
        "health": result["health"],
        # Derived counter for server-side stats aggregation (not part of the API shape).
        "needs_review_count": needs_review,
        "created_at": utcnow(),
    }


# --------------------------------------------------------------------------- #
# Analyze (extraction + health) — streamed progress, final structured result
# --------------------------------------------------------------------------- #
@router.post("/{contract_id}/analyze")
async def analyze(contract_id: str, current_user: dict = Depends(get_current_user),
                  db: AsyncIOMotorDatabase = Depends(get_database)) -> StreamingResponse:
    contract = await _owned_contract(db, contract_id, current_user["_id"])

    async def event_stream():
        queue: asyncio.Queue = asyncio.Queue()

        async def emit(message: str) -> None:
            await queue.put({"kind": "status", "message": message})

        async def run() -> None:
            try:
                result = await analyze_contract(contract, emit=emit)
                await queue.put({"kind": "result", "data": result})
            except Exception as exc:  # surface as an SSE error, never a 500 mid-stream
                await queue.put({"kind": "error", "message": str(exc)})
            finally:
                await queue.put({"kind": "done"})

        task = asyncio.create_task(run())
        try:
            while True:
                event = await queue.get()
                if event["kind"] == "done":
                    break
                if event["kind"] == "status":
                    yield _sse("status", {"message": event["message"]})
                elif event["kind"] == "error":
                    yield _sse("error", {"message": event["message"]})
                elif event["kind"] == "result":
                    doc = _analysis_doc(contract, event["data"])
                    inserted = await db.contract_analyses.insert_one(doc)
                    doc["_id"] = inserted.inserted_id
                    await db.contracts.update_one(
                        {"_id": contract["_id"]},
                        {"$set": {"status": "analyzed", "updated_at": utcnow()}},
                    )
                    await record_log(db, "analysis_run", user_id=current_user["_id"],
                                     resource_type="contract", resource_id=contract["_id"],
                                     metadata={"degraded": event["data"]["degraded"]})
                    yield _sse("result", AnalysisOut.from_doc(doc).model_dump(mode="json"))
            await task
            yield _sse("done", {})
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)


# --------------------------------------------------------------------------- #
# Chat — streamed prose tokens, final grounded citations + confidence
# --------------------------------------------------------------------------- #
@router.post("/{contract_id}/chat")
async def chat(contract_id: str, payload: ChatRequest,
               current_user: dict = Depends(get_current_user),
               db: AsyncIOMotorDatabase = Depends(get_database)) -> StreamingResponse:
    contract = await _owned_contract(db, contract_id, current_user["_id"])

    history_docs = await db.chat_messages.find(
        {"contract_id": contract["_id"]}
    ).sort("created_at", 1).to_list(length=50)
    history = [{"role": d["role"], "content": d["content"]} for d in history_docs]

    await db.chat_messages.insert_one({
        "contract_id": contract["_id"], "created_by": current_user["_id"],
        "role": "user", "content": payload.question, "citations": [],
        "confidence": None, "degraded": None, "created_at": utcnow(),
    })

    async def event_stream():
        final = None
        try:
            async for event in answer_question_stream(contract, payload.question, history=history):
                if event["type"] == "token":
                    yield _sse("token", {"text": event["text"]})
                elif event["type"] == "result":
                    final = event["data"]
                    yield _sse("result", final)
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})

        if final is not None:
            await db.chat_messages.insert_one({
                "contract_id": contract["_id"], "created_by": current_user["_id"],
                "role": "assistant", "content": final["content"],
                "citations": final.get("citations", []),
                "confidence": float(final["confidence"]),
                "degraded": bool(final["degraded"]), "created_at": utcnow(),
            })
            await record_log(db, "chat_query", user_id=current_user["_id"],
                             resource_type="contract", resource_id=contract["_id"],
                             metadata={"degraded": final["degraded"]})
        yield _sse("done", {})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)


# --------------------------------------------------------------------------- #
# Benchmark — compares the grounded analysis against seeded standards
# --------------------------------------------------------------------------- #
@router.post("/{contract_id}/benchmark")
async def benchmark(contract_id: str, current_user: dict = Depends(get_current_user),
                    db: AsyncIOMotorDatabase = Depends(get_database)) -> StreamingResponse:
    contract = await _owned_contract(db, contract_id, current_user["_id"])

    async def event_stream():
        try:
            yield _sse("status", {"message": "Loading the latest analysis…"})
            analysis = await db.contract_analyses.find_one(
                {"contract_id": contract["_id"]}, sort=[("created_at", -1)])
            if analysis is None:
                yield _sse("status", {"message": "No analysis yet — running it first…"})
                result = await analyze_contract(contract)
                analysis = _analysis_doc(contract, result)
                inserted = await db.contract_analyses.insert_one(analysis)
                analysis["_id"] = inserted.inserted_id
                await db.contracts.update_one(
                    {"_id": contract["_id"]}, {"$set": {"status": "analyzed", "updated_at": utcnow()}})

            yield _sse("status", {"message": "Comparing against benchmark standards…"})
            standard = await find_standard(db, contract["contract_type"], contract["region"])
            if standard is None:
                yield _sse("error", {"message": "No benchmark standard is available for this contract type/region."})
                yield _sse("done", {})
                return

            comparison = compare_to_standard(analysis, standard)
            degraded = bool(analysis.get("degraded", False))
            doc = {
                "contract_id": contract["_id"], "created_by": current_user["_id"],
                "contract_type": contract["contract_type"], "region": contract["region"],
                "language": contract.get("language", "en"),
                "overall_score": int(comparison["overall_score"]), "grade": comparison["grade"],
                "degraded": degraded, "confidence": float(comparison["confidence"]),
                "model": analysis.get("model", "deterministic"),
                "gaps": comparison["gaps"], "created_at": utcnow(),
            }
            inserted = await db.benchmark_results.insert_one(doc)
            doc["_id"] = inserted.inserted_id
            await record_log(db, "benchmark_run", user_id=current_user["_id"],
                             resource_type="contract", resource_id=contract["_id"])
            yield _sse("result", BenchmarkOut.from_doc(doc).model_dump(mode="json"))
        except Exception as exc:
            yield _sse("error", {"message": str(exc)})
        yield _sse("done", {})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)


# --------------------------------------------------------------------------- #
# Read endpoints
# --------------------------------------------------------------------------- #
@router.get("/{contract_id}/analysis", response_model=AnalysisOut)
async def get_analysis(contract_id: str, current_user: dict = Depends(get_current_user),
                       db: AsyncIOMotorDatabase = Depends(get_database)) -> AnalysisOut:
    contract = await _owned_contract(db, contract_id, current_user["_id"])
    doc = await db.contract_analyses.find_one(
        {"contract_id": contract["_id"]}, sort=[("created_at", -1)])
    if doc is None:
        raise not_found("Analysis")
    return AnalysisOut.from_doc(doc)


@router.get("/{contract_id}/chat", response_model=list[ChatMessageOut])
async def get_chat_history(contract_id: str, current_user: dict = Depends(get_current_user),
                           db: AsyncIOMotorDatabase = Depends(get_database)) -> list[ChatMessageOut]:
    contract = await _owned_contract(db, contract_id, current_user["_id"])
    docs = await db.chat_messages.find(
        {"contract_id": contract["_id"]}).sort("created_at", 1).to_list(length=500)
    return [ChatMessageOut.from_doc(d) for d in docs]


@router.get("/{contract_id}/benchmark", response_model=BenchmarkOut)
async def get_benchmark(contract_id: str, current_user: dict = Depends(get_current_user),
                        db: AsyncIOMotorDatabase = Depends(get_database)) -> BenchmarkOut:
    contract = await _owned_contract(db, contract_id, current_user["_id"])
    doc = await db.benchmark_results.find_one(
        {"contract_id": contract["_id"]}, sort=[("created_at", -1)])
    if doc is None:
        raise not_found("Benchmark")
    return BenchmarkOut.from_doc(doc)
