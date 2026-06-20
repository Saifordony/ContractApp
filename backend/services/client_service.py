from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException


def serialize_client(doc):
    return {"id": str(doc["_id"]), "name": doc["name"], "industry": doc.get("industry", ""), "notes": doc.get("notes", ""), "created_at": doc.get("created_at")}

async def list_clients(db, owner_user_id: str):
    docs = await db.clients.find({"owner_user_id": owner_user_id}).sort("created_at", -1).to_list(200)
    return [serialize_client(d) for d in docs]

async def create_client(db, owner_user_id: str, payload: dict):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "Client name is required.")
    now = datetime.now(timezone.utc)
    doc = {"owner_user_id": owner_user_id, "name": name, "industry": (payload.get("industry") or "").strip(), "notes": (payload.get("notes") or "").strip(), "created_at": now, "updated_at": now}
    result = await db.clients.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_client(doc)

async def assert_client_owner(db, owner_user_id: str, client_id: str | None):
    if not client_id:
        return None
    client = await db.clients.find_one({"_id": ObjectId(client_id), "owner_user_id": owner_user_id})
    if not client:
        raise HTTPException(404, "Client not found.")
    return client
