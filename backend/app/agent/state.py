"""Typed LangGraph state for the procurement agent."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, NotRequired, TypedDict


class TraceEvent(TypedDict, total=False):
    kind: Literal["thought", "action", "observation", "status"]
    node: str
    message: str
    data: dict[str, Any]


class ProcurementState(TypedDict):
    """Shared graph state. List fields use append reducers."""

    goal: str
    sku: NotRequired[str | None]
    quantity: NotRequired[int | None]
    invoice_id: NotRequired[str | None]

    vendors: Annotated[list[dict[str, Any]], operator.add]
    historical_price: NotRequired[float | None]
    contract_price: NotRequired[float | None]
    best_vendor: NotRequired[str | None]
    best_price: NotRequired[float | None]
    negotiate_vendor: NotRequired[str | None]
    negotiate_price: NotRequired[float | None]

    email_draft: NotRequired[dict[str, Any] | None]
    hitl_status: NotRequired[Literal["pending", "approved", "edited", "rejected", "skipped"]]
    hitl_decision: NotRequired[str | None]
    summary: NotRequired[str | None]
    error: NotRequired[str | None]

    # C3 re-plan / retries
    search_attempts: NotRequired[int]
    replan_done: NotRequired[bool]
    suggested_sku: NotRequired[str | None]
    original_sku: NotRequired[str | None]
    review_result: NotRequired[dict[str, Any] | None]
    finops_degraded: NotRequired[bool]

    messages: Annotated[list[str], operator.add]
    trace: Annotated[list[TraceEvent], operator.add]


def initial_state(goal: str) -> ProcurementState:
    return {
        "goal": goal,
        "sku": None,
        "quantity": None,
        "invoice_id": None,
        "vendors": [],
        "historical_price": None,
        "contract_price": None,
        "best_vendor": None,
        "best_price": None,
        "negotiate_vendor": None,
        "negotiate_price": None,
        "email_draft": None,
        "hitl_status": "pending",
        "hitl_decision": None,
        "summary": None,
        "error": None,
        "search_attempts": 0,
        "replan_done": False,
        "suggested_sku": None,
        "original_sku": None,
        "review_result": None,
        "finops_degraded": False,
        "messages": [],
        "trace": [],
    }
