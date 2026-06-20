from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.chat_service import answer_question

router = APIRouter(prefix="/genai", tags=["compatibility-chat"])

class ContractChatPayload(BaseModel):
    question: str
    contract_text: str = ""
    analysis: dict | None = None

@router.post("/contract-chat")
async def contract_chat(payload: ContractChatPayload):
    return answer_question(payload.contract_text, payload.question, payload.analysis)
