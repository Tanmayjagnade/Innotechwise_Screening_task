import re
from typing import Dict, List, Optional
from pydantic import BaseModel, field_validator


class DeclarationRequest(BaseModel):
    producer_id: str
    month: str
    declared_quantities_kg: Dict[str, float]

    @field_validator("producer_id")
    @classmethod
    def producer_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("producer_id cannot be empty")
        return v

    @field_validator("month")
    @classmethod
    def month_format(cls, v: str) -> str:
        if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", v):
            raise ValueError("month must be in YYYY-MM format (e.g. 2026-04)")
        return v

    @field_validator("declared_quantities_kg")
    @classmethod
    def quantities_non_negative(cls, v: Dict[str, float]) -> Dict[str, float]:
        if not v:
            raise ValueError("declared_quantities_kg cannot be empty")
        for category, qty in v.items():
            if qty < 0:
                raise ValueError(f"quantity for '{category}' cannot be negative")
        return v


class DeclarationResponse(BaseModel):
    record_id: str
    producer_id: str
    month: str
    declared_quantities_kg: Dict[str, float]
    timestamp: str


class ReconciliationEntry(BaseModel):
    category: str
    declared_kg: float
    procured_kg: float
    difference_kg: float
    difference_pct: float
    flagged: bool


class SummaryResponse(BaseModel):
    producer_id: str
    month: str
    reconciliation: List[ReconciliationEntry]
    flags: List[ReconciliationEntry]
    narrative: str


class AskRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def question_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question cannot be empty")
        return v


class Citation(BaseModel):
    document: str
    section: str


class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]
