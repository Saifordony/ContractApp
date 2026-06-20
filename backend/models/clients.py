"""Client domain models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.models.common import Email, OutBase


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: Optional[Email] = None
    company: Optional[str] = Field(default=None, max_length=160)
    notes: Optional[str] = Field(default=None, max_length=4000)


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    email: Optional[Email] = None
    company: Optional[str] = Field(default=None, max_length=160)
    notes: Optional[str] = Field(default=None, max_length=4000)


class ClientOut(OutBase):
    id: str
    name: str
    email: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
