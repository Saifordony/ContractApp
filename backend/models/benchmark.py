"""Benchmark response models."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from backend.models.analysis import EvidenceOut
from backend.models.common import OutBase


class GapOut(BaseModel):
    clause_key: str
    importance: str
    benchmark_expectation: str
    contract_status: str
    severity: str
    recommendation: str
    evidence: list[EvidenceOut] = []


class BenchmarkOut(OutBase):
    id: str
    contract_id: str
    contract_type: str
    region: str
    overall_score: int
    grade: str
    degraded: bool
    confidence: float
    gaps: list[GapOut]
    created_at: datetime
