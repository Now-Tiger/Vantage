from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ────────────────────────────── Document types recognized by the segregator ──────────────────────────────

class DocumentType(str, Enum):
    CLAIM_FORM = "claim_forms"
    CHEQUE_OR_BANK = "cheque_or_bank_details"
    IDENTITY = "identity_document"
    ITEMIZED_BILL = "itemized_bill"
    DISCHARGE_SUMMARY = "discharge_summary"
    PRESCRIPTION = "prescription"
    INVESTIGATION_REPORT = "investigation_report"
    CASH_RECEIPT = "cash_receipt"
    OTHER = "other"


# ────────────────────────────── Per-page data extracted from the PDF ─────────────────────────────────────

class PageData(BaseModel):
    page_number: int
    text: str


# ────────────────────────────── Segregator output (per page) ────────────────────────────────────────────

class PageClassification(BaseModel):
    page_number: int
    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)


# ────────────────────────────── Extraction agent outputs ────────────────────────────────────────────────

class IdentityInfo(BaseModel):
    patient_name: str | None = None
    date_of_birth: str | None = None
    id_numbers: list[str] = Field(default_factory=list)
    policy_number: str | None = None
    policy_details: dict[str, Any] = Field(default_factory=dict)


class DischargeSummaryInfo(BaseModel):
    diagnosis: list[str] = Field(default_factory=list)
    admission_date: str | None = None
    discharge_date: str | None = None
    physician_name: str | None = None
    physician_details: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None


class BillLineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float


class ItemizedBillInfo(BaseModel):
    items: list[BillLineItem] = Field(default_factory=list)
    total_amount: float | None = None


# ────────────────────────────── API request / response ──────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    claim_id: str


class ProcessResponse(BaseModel):
    claim_id: str
    segregation: list[PageClassification]
    identity: IdentityInfo | None = None
    discharge_summary: DischargeSummaryInfo | None = None
    itemized_bill: ItemizedBillInfo | None = None


class ClaimSummary(BaseModel):
    claim_id: str
    status: str
    created_at: datetime


class ClaimListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ClaimSummary]
