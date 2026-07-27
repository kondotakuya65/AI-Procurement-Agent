"""Graph node stubs — real tool wiring lands in C2+."""

from __future__ import annotations

from typing import Any

from app.agent.state import ProcurementState, TraceEvent


def _trace(
    node: str,
    message: str,
    *,
    kind: str = "status",
    data: dict[str, Any] | None = None,
) -> list[TraceEvent]:
    event: TraceEvent = {"kind": kind, "node": node, "message": message}  # type: ignore[typeddict-item]
    if data:
        event["data"] = data
    return [event]


def parse_goal(state: ProcurementState) -> dict[str, Any]:
    """Stub: extract sku/qty later with regex / LLM."""
    return {
        "messages": [f"parse_goal: received goal ({len(state.get('goal') or '')} chars)"],
        "trace": _trace(
            "parse_goal",
            "Parsed goal (stub — C2 fills SKU/qty).",
            kind="thought",
        ),
    }


def search_vendors_node(state: ProcurementState) -> dict[str, Any]:
    return {
        "messages": ["search_vendors: stub"],
        "trace": _trace(
            "search_vendors",
            "Would call search_vendors tool (stub).",
            kind="action",
        ),
    }


def query_finops_node(state: ProcurementState) -> dict[str, Any]:
    return {
        "messages": ["query_finops: stub"],
        "trace": _trace(
            "query_finops",
            "Would call query_finops_rag (stub).",
            kind="action",
        ),
    }


def compare_offers_node(state: ProcurementState) -> dict[str, Any]:
    return {
        "messages": ["compare_offers: stub"],
        "trace": _trace(
            "compare_offers",
            "Would compare vendor quotes vs FinOps history (stub).",
            kind="thought",
        ),
    }


def draft_email_node(state: ProcurementState) -> dict[str, Any]:
    return {
        "messages": ["draft_email: stub"],
        "email_draft": {
            "subject": "(stub)",
            "body": "Draft placeholder — C2 wires draft_email tool.",
            "vendor": state.get("negotiate_vendor") or state.get("best_vendor"),
        },
        "trace": _trace(
            "draft_email",
            "Would draft negotiation email (stub).",
            kind="action",
        ),
    }


def hitl_gate_node(state: ProcurementState) -> dict[str, Any]:
    """Stub gate — C4 adds interrupt() / resume."""
    return {
        "hitl_status": state.get("hitl_status") or "pending",
        "messages": ["hitl_gate: stub pending"],
        "trace": _trace(
            "hitl_gate",
            "HITL gate reached (stub — interrupt in C4).",
            kind="status",
        ),
    }


def finalize_node(state: ProcurementState) -> dict[str, Any]:
    return {
        "summary": state.get("summary")
        or "Skeleton run complete. Happy-path tools land in C2.",
        "messages": ["finalize: stub"],
        "trace": _trace(
            "finalize",
            "Run finalized (stub).",
            kind="status",
        ),
    }
