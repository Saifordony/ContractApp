"""Chat request/response models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.models.common import OutBase


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class CitationOut(BaseModel):
    text: str
    char_start: int
    char_end: int


class ChatMessageOut(OutBase):
    id: str
    role: str
    content: str
    citations: list[CitationOut] = []
    confidence: Optional[float] = None
    degraded: Optional[bool] = None
    created_at: datetime
