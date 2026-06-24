"""Pydantic request/response models shared across backend.main and backend.routers."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class User(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Client(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class Contract(BaseModel):
    title: str
    client_id: str
    content: Optional[str] = None
    status: str = "pending"


class ContractAnalysis(BaseModel):
    contract_id: str
    clauses: Dict[str, str]
    evaluation: Dict[str, Any]
    created_at: datetime


class ContractTextAnalysisRequest(BaseModel):
    contract_text: str
    response_language: str = "english"


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class ContractChatRequest(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None
    chat_history: list[ChatHistoryMessage] = []
    response_language: str = "english"
    response_mode: str = "ask_anything"
    debug: bool = False


class PipelineOpportunity(BaseModel):
    client: str
    opportunity_name: str
    stage: str
    value: float
    expected_close_date: Optional[str] = None
    last_updated: Optional[str] = None
    owner: Optional[str] = None
    close_target: Optional[float] = 0


class PipelineAnalysisRequest(BaseModel):
    opportunities: list[PipelineOpportunity]
    stage_probabilities: Optional[Dict[str, float]] = None


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class ContractCompareRequest(BaseModel):
    contract_id_a: str
    contract_id_b: str


class ContractChatTextRequest(BaseModel):
    message: Optional[str] = None
    question: Optional[str] = None
    contract_text: str = ""
    analysis_results: Optional[Dict[str, Any]] = None
    chat_history: list[ChatHistoryMessage] = []
    response_language: str = "english"
    response_mode: str = "ask_anything"
    debug: bool = False
