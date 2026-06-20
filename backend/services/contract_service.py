from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from backend.services.analysis_service import extract_text
from backend.services.client_service import assert_client_owner


def _object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(422, "Invalid contract id or request payload.") from exc


def serialize_contract(doc):
    return {"id": str(doc["_id"]), "name": doc["name"], "client_id": doc.get("client_id"), "filename": doc.get("filename"), "extracted_text": doc.get("extracted_text", ""), "analysis_summary": doc.get("analysis_summary"), "created_at": doc.get("created_at")}


async def list_contracts(db, owner_user_id: str):
    docs = await db.contracts.find({"owner_user_id": owner_user_id}).sort("created_at", -1).to_list(200)
    return [serialize_contract(d) for d in docs]


async def get_contract(db, owner_user_id: str, contract_id: str):
    oid = _object_id(contract_id)
    doc = await db.contracts.find_one({"_id": oid, "owner_user_id": owner_user_id})
    if doc:
        return doc
    exists = await db.contracts.find_one({"_id": oid})
    if exists:
        raise HTTPException(403, "You do not have access to this contract.")
    raise HTTPException(404, "Contract not found.")


async def upload_contract(db, owner_user_id: str, filename: str, content: bytes, client_id: str | None = None, name: str | None = None):
    await assert_client_owner(db, owner_user_id, client_id)
    text = extract_text(filename, content)
    if not text.strip():
        raise HTTPException(422, "No readable text could be extracted from this contract.")
    now = datetime.now(timezone.utc)
    doc = {"owner_user_id": owner_user_id, "client_id": client_id, "name": name or filename, "filename": filename, "extracted_text": text, "created_at": now, "updated_at": now}
    result = await db.contracts.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_contract(doc)
