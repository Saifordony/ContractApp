"""Client CRUD endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from backend import main as _main
from backend.models import Client

router = APIRouter()


@router.post("/clients")
async def create_client(client: Client, current_user: dict = Depends(_main.get_current_user)):
    """Create a new client"""
    client_dict = client.dict()
    client_dict["created_at"] = datetime.utcnow()
    client_dict["created_by"] = current_user["username"]

    result = await _main.db.clients.insert_one(client_dict)
    return {
        "message": "Client created successfully",
        "client_id": str(result.inserted_id),
    }


@router.get("/clients")
async def get_clients(current_user: dict = Depends(_main.get_current_user)):
    """Get all clients for the current user"""
    clients = await _main.db.clients.find({"created_by": current_user["username"]}).to_list(
        100
    )

    for client in clients:
        client["_id"] = str(client["_id"])

    return {"clients": clients}


@router.get("/clients/{client_id}")
async def get_client(client_id: str, current_user: dict = Depends(_main.get_current_user)):
    """Get a specific client by ID"""
    object_id = _main.parse_object_id(client_id, "client ID")
    client = await _main.db.clients.find_one({"_id": object_id})

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    client["_id"] = str(client["_id"])
    return client


@router.put("/clients/{client_id}")
async def update_client(
    client_id: str, client: Client, current_user: dict = Depends(_main.get_current_user)
):
    """Update a client"""
    object_id = _main.parse_object_id(client_id, "client ID")

    existing_client = await _main.db.clients.find_one({"_id": object_id})
    if not existing_client:
        raise HTTPException(status_code=404, detail="Client not found")

    if existing_client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    client_dict = client.dict()
    client_dict["updated_at"] = datetime.utcnow()
    client_dict["updated_by"] = current_user["username"]

    result = await _main.db.clients.update_one(
        {"_id": object_id}, {"$set": client_dict}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"message": "Client updated successfully"}


@router.delete("/clients/{client_id}")
async def delete_client(client_id: str, current_user: dict = Depends(_main.get_current_user)):
    """Delete a client"""
    object_id = _main.parse_object_id(client_id, "client ID")

    existing_client = await _main.db.clients.find_one({"_id": object_id})
    if not existing_client:
        raise HTTPException(status_code=404, detail="Client not found")

    if existing_client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    contracts = await _main.db.contracts.find({"client_id": client_id}).to_list(1)
    if contracts:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete client with existing contracts. Delete contracts first.",
        )

    result = await _main.db.clients.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"message": "Client deleted successfully"}


@router.get("/clients/{client_id}/contracts")
async def get_client_contracts(
    client_id: str, current_user: dict = Depends(_main.get_current_user)
):
    """Get all contracts for a specific client"""
    object_id = _main.parse_object_id(client_id, "client ID")

    client = await _main.db.clients.find_one({"_id": object_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    contracts = await _main.db.contracts.find({"client_id": client_id}).to_list(100)

    for contract in contracts:
        contract["_id"] = str(contract["_id"])

    return {"contracts": contracts}
