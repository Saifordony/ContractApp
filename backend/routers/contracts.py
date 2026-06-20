"""Contract CRUD, GenAI initialization, chat, and cross-contract comparison."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from backend import main as _main
from backend.models import Contract, ContractChatRequest, ContractCompareRequest
from backend.services.contract_analysis_service import analyze_contract_text, normalize_analysis_results
from backend.services.contract_chat_service import build_contract_chat_response, classify_chat_intent

router = APIRouter()


@router.post("/contracts")
async def create_contract(
    contract: Contract, current_user: dict = Depends(_main.get_current_user)
):
    """Create a new contract"""
    client_object_id = _main.parse_object_id(contract.client_id, "client ID")

    client = await _main.db.clients.find_one({"_id": client_object_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied to client")

    contract_dict = contract.dict()
    contract_dict["created_at"] = datetime.utcnow()
    contract_dict["created_by"] = current_user["username"]

    result = await _main.db.contracts.insert_one(contract_dict)
    return {
        "message": "Contract created successfully",
        "contract_id": str(result.inserted_id),
    }


@router.get("/contracts")
async def get_contracts(current_user: dict = Depends(_main.get_current_user)):
    """Get all contracts for the current user"""
    contracts = await _main.db.contracts.find(
        {"created_by": current_user["username"]}
    ).to_list(100)

    for contract in contracts:
        contract["_id"] = str(contract["_id"])

    return {"contracts": contracts}


@router.get("/contracts/{contract_id}")
async def get_contract(
    contract_id: str, current_user: dict = Depends(_main.get_current_user)
):
    """Get a specific contract by ID"""
    object_id = _main.parse_object_id(contract_id, "contract ID")

    contract = await _main.db.contracts.find_one({"_id": object_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    contract["_id"] = str(contract["_id"])
    return contract


@router.put("/contracts/{contract_id}")
async def update_contract(
    contract_id: str, contract: Contract, current_user: dict = Depends(_main.get_current_user)
):
    """Update a contract"""
    object_id = _main.parse_object_id(contract_id, "contract ID")
    client_object_id = _main.parse_object_id(contract.client_id, "client ID")

    existing_contract = await _main.db.contracts.find_one({"_id": object_id})
    if not existing_contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if existing_contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    client = await _main.db.clients.find_one({"_id": client_object_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied to client")

    contract_dict = contract.dict()
    contract_dict["updated_at"] = datetime.utcnow()
    contract_dict["updated_by"] = current_user["username"]

    result = await _main.db.contracts.update_one(
        {"_id": object_id}, {"$set": contract_dict}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {"message": "Contract updated successfully"}


@router.delete("/contracts/{contract_id}")
async def delete_contract(
    contract_id: str, current_user: dict = Depends(_main.get_current_user)
):
    """Delete a contract"""
    object_id = _main.parse_object_id(contract_id, "contract ID")

    existing_contract = await _main.db.contracts.find_one({"_id": object_id})
    if not existing_contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if existing_contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    await _main.db.contract_analyses.delete_many({"contract_id": contract_id})

    result = await _main.db.contracts.delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {"message": "Contract deleted successfully"}


@router.post("/contracts/{contract_id}/init-genai")
async def init_genai_analysis(
    contract_id: str,
    response_language: str = Query("english"),
    current_user: dict = Depends(_main.get_current_user),
):
    """Compatibility wrapper: save canonical analysis for a stored contract."""
    object_id = _main.parse_object_id(contract_id, "contract ID")

    contract = await _main.db.contracts.find_one({"_id": object_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if not contract.get("content"):
        raise HTTPException(status_code=400, detail="Contract has no content to analyze")

    try:
        results = await analyze_contract_text(contract["content"], response_language=response_language)
        analysis_dict = {
            "contract_id": contract_id,
            "schema_version": results.get("schema_version"),
            "results": results,
            "created_at": datetime.utcnow(),
            "created_by": current_user["username"],
        }

        result = await _main.db.contract_analyses.insert_one(analysis_dict)
        await _main.db.contracts.update_one(
            {"_id": object_id},
            {"$set": {"status": "analyzed", "analysis_id": str(result.inserted_id)}},
        )

        return {"message": "GenAI analysis completed", "analysis_id": str(result.inserted_id), "results": results}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        print(f"/contracts/{contract_id}/init-genai failed: {exc}")
        raise HTTPException(status_code=500, detail="Contract analysis failed. Please try again.")


@router.post("/contracts/{contract_id}/chat")
async def chat_with_contract(
    contract_id: str,
    request: ContractChatRequest,
    current_user: dict = Depends(_main.get_current_user),
):
    object_id = _main.parse_object_id(contract_id, "contract ID")

    contract = await _main.db.contracts.find_one({"_id": object_id})
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.get("created_by") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied")

    message = (request.message or request.question or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please enter a message for the contract assistant.")

    intent, _ = classify_chat_intent(message)
    context_free_intents = {"small_talk", "app_help", "unsafe_request", "clarification_needed", "general_business_question"}
    if not contract.get("content") and intent not in context_free_intents:
        raise HTTPException(status_code=400, detail="Please analyze this contract before using the assistant.")

    try:
        latest_analysis = await _main.db.contract_analyses.find_one(
            {"contract_id": contract_id},
            sort=[("created_at", -1)],
        )
        analysis_results = normalize_analysis_results((latest_analysis or {}).get("results", {}))
        chat_history = [item.dict() for item in request.chat_history]
        structured_answer = build_contract_chat_response(
            message=message,
            contract_text=contract["content"],
            analysis_results=analysis_results,
            benchmark_result=contract.get("benchmark_result"),
            chat_history=chat_history,
            response_language=request.response_language,
            response_mode=request.response_mode,
            debug=request.debug,
        )

        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": f"/contracts/{contract_id}/chat",
                "action": "contract_chat",
                "timestamp": datetime.utcnow(),
                "status": "success",
                "evidence_count": len(structured_answer.get("evidence_snippets", [])),
                "confidence": structured_answer.get("confidence", "Low"),
                "intent": (structured_answer.get("debug") or {}).get("intent", structured_answer.get("answer_type", "unknown")),
                "prompt_preview": message[:200],
                "output_preview": structured_answer.get("answer", "")[:240],
            }
        )

        return structured_answer
    except HTTPException:
        raise
    except Exception as e:
        await _main.db.logs.insert_one(
            {
                "user": current_user["username"],
                "endpoint": f"/contracts/{contract_id}/chat",
                "action": "contract_chat",
                "timestamp": datetime.utcnow(),
                "status": "error",
                "error": str(e),
            }
        )
        raise HTTPException(status_code=500, detail="The contract assistant hit an unexpected error. Please try again.")


@router.post("/contracts/compare")
async def compare_contracts(
    payload: ContractCompareRequest, current_user: dict = Depends(_main.get_current_user)
):
    """Compare the latest analyses of two of the user's contracts clause by clause.

    Returns each contract's title and health score, a per-clause status/text diff
    with a plain-English difference summary, and an overall recommendation.
    """
    async def _load(contract_id: str):
        object_id = _main.parse_object_id(contract_id, "contract ID")
        contract = await _main.db.contracts.find_one({"_id": object_id})
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        if contract.get("created_by") != current_user["username"]:
            raise HTTPException(status_code=403, detail="Access denied")
        analysis = await _main.db.contract_analyses.find_one(
            {"contract_id": contract_id}, sort=[("created_at", -1)]
        )
        results = (analysis or {}).get("results", {}) if isinstance(analysis, dict) else {}
        return contract, results

    contract_a, results_a = await _load(payload.contract_id_a)
    contract_b, results_b = await _load(payload.contract_id_b)

    def _clauses(results: Dict[str, Any]) -> Dict[str, Any]:
        structured = results.get("structured_clauses", {}) if isinstance(results, dict) else {}
        clauses = structured.get("clauses", {}) if isinstance(structured, dict) else {}
        return clauses if isinstance(clauses, dict) else {}

    clauses_a = _clauses(results_a)
    clauses_b = _clauses(results_b)

    clause_diff = []
    for clause_type in sorted(set(clauses_a) | set(clauses_b)):
        a = clauses_a.get(clause_type, {}) if isinstance(clauses_a.get(clause_type), dict) else {}
        b = clauses_b.get(clause_type, {}) if isinstance(clauses_b.get(clause_type), dict) else {}
        status_a = str(a.get("status", "missing"))
        status_b = str(b.get("status", "missing"))
        text_a = str(a.get("extracted_text") or "")
        text_b = str(b.get("extracted_text") or "")
        clause_diff.append(
            {
                "clause_type": clause_type,
                "status_a": status_a,
                "status_b": status_b,
                "text_a": text_a,
                "text_b": text_b,
                "difference_summary": _main._clause_difference_summary(
                    clause_type, status_a, text_a, status_b, text_b
                ),
            }
        )

    def _health_score(results: Dict[str, Any]) -> int:
        health = results.get("health_evaluation", {}) if isinstance(results, dict) else {}
        try:
            return int(health.get("health_score") or 0)
        except (TypeError, ValueError):
            return 0

    score_a = _health_score(results_a)
    score_b = _health_score(results_b)
    if score_a == score_b:
        recommendation = "Both contracts score similarly; review the clause differences before deciding."
    else:
        stronger = contract_a if score_a > score_b else contract_b
        recommendation = (
            f"'{stronger.get('title', 'the higher-scoring contract')}' is the stronger contract "
            f"({max(score_a, score_b)} vs {min(score_a, score_b)} health score), but confirm the "
            "clause-level differences match your priorities."
        )

    return {
        "contract_a_title": contract_a.get("title", ""),
        "contract_b_title": contract_b.get("title", ""),
        "clause_diff": clause_diff,
        "health_score_a": score_a,
        "health_score_b": score_b,
        "recommendation": recommendation,
    }
