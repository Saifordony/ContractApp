"""Contract CRUD + document upload, scoped to the authenticated owner."""
from __future__ import annotations

import re
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.database import get_database
from backend.dependencies import get_current_user
from backend.errors import ApiError, not_found
from backend.models.common import Page, utcnow
from backend.models.contracts import ContractCreate, ContractListItem, ContractOut, ContractUpdate
from backend.services.audit import record_log
from backend.services.document_parsing import detect_language, parse_document

router = APIRouter(prefix="/contracts", tags=["contracts"])


def _oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise not_found("Contract")
    return ObjectId(value)


async def _resolve_client(db: AsyncIOMotorDatabase, owner: ObjectId, client_id: Optional[str]) -> Optional[ObjectId]:
    if not client_id:
        return None
    if not ObjectId.is_valid(client_id):
        raise ApiError(400, "Invalid client_id", "invalid_client")
    oid = ObjectId(client_id)
    if await db.clients.find_one({"_id": oid, "created_by": owner}) is None:
        raise ApiError(400, "Client does not exist", "invalid_client")
    return oid


async def _owned_contract(db: AsyncIOMotorDatabase, contract_id: str, owner: ObjectId) -> dict:
    doc = await db.contracts.find_one({"_id": _oid(contract_id), "created_by": owner})
    if doc is None:
        raise not_found("Contract")
    return doc


@router.get("", response_model=Page[ContractListItem])
async def list_contracts(
    search: str | None = Query(None),
    client_id: str | None = Query(None),
    contract_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Page[ContractListItem]:
    query: dict = {"created_by": current_user["_id"]}
    if search:
        query["title"] = {"$regex": re.escape(search), "$options": "i"}
    if client_id and ObjectId.is_valid(client_id):
        query["client_id"] = ObjectId(client_id)
    if contract_type:
        query["contract_type"] = contract_type
    if status_filter:
        query["status"] = status_filter

    total = await db.contracts.count_documents(query)
    cursor = db.contracts.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = [ContractListItem.from_doc(doc) async for doc in cursor]
    return Page(items=items, total=total)


@router.post("", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ContractOut:
    client_oid = await _resolve_client(db, current_user["_id"], payload.client_id)
    language = payload.language or detect_language(payload.content)
    now = utcnow()
    doc = {
        "created_by": current_user["_id"],
        "client_id": client_oid,
        "title": payload.title,
        "contract_type": payload.contract_type,
        "region": payload.region,
        "language": language,
        "source_format": "text",
        "content": payload.content,
        "page_count": None,
        "ocr_used": False,
        "status": "uploaded",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.contracts.insert_one(doc)
    doc["_id"] = result.inserted_id
    await record_log(db, "contract_create", user_id=current_user["_id"],
                     resource_type="contract", resource_id=result.inserted_id)
    return ContractOut.from_doc(doc)


@router.post("/upload", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def upload_contract(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    contract_type: str = Form("general"),
    region: str = Form("US"),
    client_id: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ContractOut:
    data = await file.read()
    if not data:
        raise ApiError(400, "Uploaded file is empty", "empty_file")
    try:
        parsed = parse_document(file.filename or "", data, file.content_type)
    except ValueError as exc:
        raise ApiError(400, str(exc), "unsupported_file")
    except Exception as exc:  # native parser failure
        raise ApiError(422, f"Could not parse document: {exc}", "parse_error")
    if not parsed.text.strip():
        raise ApiError(422, "No extractable text found in the document", "empty_document")

    client_oid = await _resolve_client(db, current_user["_id"], client_id)
    lang = language if language in ("en", "ar") else detect_language(parsed.text)
    now = utcnow()
    doc = {
        "created_by": current_user["_id"],
        "client_id": client_oid,
        "title": title or file.filename or "Untitled contract",
        "contract_type": contract_type,
        "region": region,
        "language": lang,
        "source_format": parsed.source_format,
        "content": parsed.text,
        "page_count": parsed.page_count,
        "ocr_used": parsed.ocr_used,
        "status": "uploaded",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.contracts.insert_one(doc)
    doc["_id"] = result.inserted_id
    await record_log(db, "contract_create", user_id=current_user["_id"],
                     resource_type="contract", resource_id=result.inserted_id,
                     metadata={"source_format": parsed.source_format, "ocr_used": parsed.ocr_used})
    return ContractOut.from_doc(doc)


@router.get("/{contract_id}", response_model=ContractOut)
async def get_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ContractOut:
    doc = await _owned_contract(db, contract_id, current_user["_id"])
    return ContractOut.from_doc(doc)


@router.patch("/{contract_id}", response_model=ContractOut)
async def update_contract(
    contract_id: str,
    payload: ContractUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ContractOut:
    doc = await _owned_contract(db, contract_id, current_user["_id"])
    updates = payload.model_dump(exclude_none=True)
    if "client_id" in updates:
        updates["client_id"] = await _resolve_client(db, current_user["_id"], updates["client_id"])
    if updates:
        updates["updated_at"] = utcnow()
        await db.contracts.update_one({"_id": doc["_id"]}, {"$set": updates})
        await record_log(db, "contract_update", user_id=current_user["_id"],
                         resource_type="contract", resource_id=doc["_id"])
    refreshed = await db.contracts.find_one({"_id": doc["_id"]})
    return ContractOut.from_doc(refreshed)


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(
    contract_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Response:
    doc = await _owned_contract(db, contract_id, current_user["_id"])
    oid = doc["_id"]
    await db.contracts.delete_one({"_id": oid})
    # Cascade: a contract's analyses, chat, and benchmark results go with it.
    await db.contract_analyses.delete_many({"contract_id": oid})
    await db.chat_messages.delete_many({"contract_id": oid})
    await db.benchmark_results.delete_many({"contract_id": oid})
    await record_log(db, "contract_delete", user_id=current_user["_id"],
                     resource_type="contract", resource_id=oid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
