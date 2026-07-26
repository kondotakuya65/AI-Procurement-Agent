"""Pydantic contracts for agent tools (I/O + ToolResult)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, model_validator


class ToolName(str, Enum):
    SEARCH_VENDORS = "search_vendors"
    QUERY_FINOPS_RAG = "query_finops_rag"
    REVIEW_INVOICE = "review_invoice"
    DRAFT_EMAIL = "draft_email"


class ToolStatus(str, Enum):
    OK = "ok"
    EMPTY = "empty"
    ERROR = "error"


T = TypeVar("T")


class ToolResult(BaseModel, Generic[T]):
    """Uniform wrapper so the graph / SSE can log Observation consistently."""

    tool: ToolName
    status: ToolStatus = ToolStatus.OK
    data: T | None = None
    error: str | None = None
    observation: str = Field(
        ...,
        description="Short human-readable summary for Thought/Action/Observation traces.",
    )
    latency_ms: float | None = None

    @model_validator(mode="after")
    def _error_requires_status(self) -> ToolResult[T]:
        if self.status == ToolStatus.ERROR and not self.error:
            raise ValueError("error message required when status=error")
        if self.status != ToolStatus.ERROR and self.error:
            raise ValueError("error must be unset unless status=error")
        return self

    @classmethod
    def ok(
        cls,
        tool: ToolName,
        data: T,
        observation: str,
        *,
        latency_ms: float | None = None,
    ) -> ToolResult[T]:
        return cls(
            tool=tool,
            status=ToolStatus.OK,
            data=data,
            observation=observation,
            latency_ms=latency_ms,
        )

    @classmethod
    def empty(
        cls,
        tool: ToolName,
        observation: str,
        *,
        data: T | None = None,
        latency_ms: float | None = None,
    ) -> ToolResult[T]:
        return cls(
            tool=tool,
            status=ToolStatus.EMPTY,
            data=data,
            observation=observation,
            latency_ms=latency_ms,
        )

    @classmethod
    def fail(
        cls,
        tool: ToolName,
        error: str,
        *,
        observation: str | None = None,
        latency_ms: float | None = None,
    ) -> ToolResult[T]:
        return cls(
            tool=tool,
            status=ToolStatus.ERROR,
            error=error,
            observation=observation or f"{tool.value} failed: {error}",
            latency_ms=latency_ms,
        )


# --- search_vendors ---


class SearchVendorsInput(BaseModel):
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    include_alternates: bool = False


class VendorOffer(BaseModel):
    offer_id: str
    vendor: str
    sku: str
    description: str = ""
    unit_price: float
    currency: str = "USD"
    moq: int = 0
    available_qty: int = 0
    lead_days: int = 0
    payment_terms: str = ""
    notes: str | None = None


class SearchVendorsData(BaseModel):
    sku: str
    quantity: int
    offers: list[VendorOffer] = Field(default_factory=list)
    best_offer: VendorOffer | None = None


# --- query_finops_rag ---


class QueryFinopsInput(BaseModel):
    question: str = Field(..., min_length=1)
    sku: str | None = None
    vendor: str | None = None


class QueryFinopsData(BaseModel):
    answer: str
    facts: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(
        default="mock",
        description="mock | live — which FinOps backend answered.",
    )
    historical_unit_price: float | None = None
    contract_unit_price: float | None = None


# --- review_invoice ---


class ReviewInvoiceInput(BaseModel):
    invoice_id: str = Field(..., min_length=1)


class ReviewRecommendation(str, Enum):
    ACCEPT = "Accept"
    REJECT = "Reject"


class ReviewInvoiceData(BaseModel):
    invoice_id: str
    vendor: str | None = None
    po_number: str | None = None
    sku: str | None = None
    invoice_unit_price: float | None = None
    contract_unit_price: float | None = None
    drift_pct: float | None = None
    max_price_drift_pct: float | None = None
    po_match: bool | None = None
    recommendation: ReviewRecommendation
    rationale: str = ""


# --- draft_email ---


class DraftEmailInput(BaseModel):
    vendor: str = Field(..., min_length=1)
    sku: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    quoted_unit_price: float = Field(..., gt=0)
    target_unit_price: float | None = Field(
        default=None,
        description="Historical/contract/best-comp price to negotiate toward.",
    )
    intent: str = Field(
        default="negotiate_price",
        description="negotiate_price | request_quote | decline",
    )
    context: str = Field(
        default="",
        description="Extra facts for the LLM (spend, competitors, PO).",
    )


class DraftEmailData(BaseModel):
    vendor: str
    subject: str
    body: str
    intent: str


# --- HITL resume (used by API later; defined here for one contract home) ---


class HitlDecision(str, Enum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class HitlResumeInput(BaseModel):
    decision: HitlDecision
    edited_draft: str | None = None

    @model_validator(mode="after")
    def _edit_requires_draft(self) -> HitlResumeInput:
        if self.decision == HitlDecision.EDIT and not (self.edited_draft or "").strip():
            raise ValueError("edited_draft is required when decision=edit")
        return self
