"""Client CRUD, scoped to the authenticated owner."""
from __future__ import annotations

import re

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.database import get_database
from backend.dependencies import get_current_user
from backend.errors import ApiError, not_found
from backend.models.clients import ClientCreate, ClientOut, ClientUpdate
from backend.models.common import Page, utcnow
from backend.services.audit import record_log

router = APIRouter(prefix="/clients", tags=["clients"])


def _oid(value: str) -> ObjectId:
    if not ObjectId.is_valid(value):
        raise not_found("Client")
    return ObjectId(value)


@router.get("", response_model=Page[ClientOut])
async def list_clients(
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Page[ClientOut]:
    query: dict = {"created_by": current_user["_id"]}
    if search:
        query["name"] = {"$regex": re.escape(search), "$options": "i"}
    total = await db.clients.count_documents(query)
    cursor = db.clients.find(query).sort("name", 1).skip(skip).limit(limit)
    items = [ClientOut.from_doc(doc) async for doc in cursor]
    return Page(items=items, total=total)


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ClientOut:
    now = utcnow()
    doc = {
        "created_by": current_user["_id"],
        "name": payload.name,
        "email": payload.email,
        "company": payload.company,
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.clients.insert_one(doc)
    doc["_id"] = result.inserted_id
    await record_log(db, "client_create", user_id=current_user["_id"],
                     resource_type="client", resource_id=result.inserted_id)
    return ClientOut.from_doc(doc)


@router.get("/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ClientOut:
    doc = await db.clients.find_one({"_id": _oid(client_id), "created_by": current_user["_id"]})
    if doc is None:
        raise not_found("Client")
    return ClientOut.from_doc(doc)


@router.patch("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: str,
    payload: ClientUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> ClientOut:
    updates = payload.model_dump(exclude_none=True)
    oid = _oid(client_id)
    if updates:
        updates["updated_at"] = utcnow()
        result = await db.clients.update_one(
            {"_id": oid, "created_by": current_user["_id"]}, {"$set": updates}
        )
        if result.matched_count == 0:
            raise not_found("Client")
        await record_log(db, "client_update", user_id=current_user["_id"],
                         resource_type="client", resource_id=oid)
    doc = await db.clients.find_one({"_id": oid, "created_by": current_user["_id"]})
    if doc is None:
        raise not_found("Client")
    return ClientOut.from_doc(doc)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> Response:
    oid = _oid(client_id)
    result = await db.clients.delete_one({"_id": oid, "created_by": current_user["_id"]})
    if result.deleted_count == 0:
        raise not_found("Client")
    # Detach contracts that referenced this client (do not delete the contracts).
    await db.contracts.update_many(
        {"client_id": oid, "created_by": current_user["_id"]}, {"$set": {"client_id": None}}
    )
    await record_log(db, "client_delete", user_id=current_user["_id"],
                     resource_type="client", resource_id=oid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
