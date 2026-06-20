"""Analysis response models (one canonical shape)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from backend.models.common import OutBase


class EvidenceOut(BaseModel):
    text: str
    char_start: int
    char_end: int
    chunk_id: Optional[int] = None


class ClauseOut(BaseModel):
    key: str
    label: dict
    status: str
    extracted_text: str
    explanation: str
    evidence: list[EvidenceOut] = []
    confidence: float


class DimensionOut(BaseModel):
    key: str
    label: dict
    score: int
    explanation: str
    evidence: list[EvidenceOut] = []


class HealthOut(BaseModel):
    overall_score: int
    grade: str
    dimensions: list[DimensionOut]
    confidence: float


class AnalysisOut(OutBase):
    id: str
    contract_id: str
    language: str
    degraded: bool
    model: str
    confidence: float
    clauses: list[ClauseOut]
    health: HealthOut
    created_at: datetime
