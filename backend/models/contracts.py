"""Contract domain models."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.models.common import OutBase

Language = Literal["en", "ar"]
SourceFormat = Literal["pdf", "docx", "text"]
ContractStatus = Literal["uploaded", "analyzed"]


class ContractCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    contract_type: str = Field(default="general", max_length=60)
    region: str = Field(default="US", max_length=60)
    language: Optional[Language] = None  # auto-detected when omitted
    client_id: Optional[str] = None
    content: str = Field(min_length=1)


class ContractUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    contract_type: Optional[str] = Field(default=None, max_length=60)
    region: Optional[str] = Field(default=None, max_length=60)
    language: Optional[Language] = None
    client_id: Optional[str] = None
    status: Optional[ContractStatus] = None


class ContractOut(OutBase):
    id: str
    created_by: str
    client_id: Optional[str] = None
    title: str
    contract_type: str
    region: str
    language: str
    source_format: str
    content: str
    page_count: Optional[int] = None
    ocr_used: bool = False
    status: str
    created_at: datetime
    updated_at: datetime


class ContractListItem(OutBase):
    """List view — omits the (potentially large) ``content`` field."""

    id: str
    client_id: Optional[str] = None
    title: str
    contract_type: str
    region: str
    language: str
    status: str
    created_at: datetime
    updated_at: datetime
