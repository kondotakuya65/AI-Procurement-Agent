"""Procurement graph nodes — happy path + re-plan / retries (C3)."""

from __future__ import annotations

from typing import Any, Literal

from app.agent.parse import extract_invoice_id, extract_quantity, extract_sku
from app.agent.replan import suggest_similar_sku
from app.agent.state import ProcurementState, TraceEvent
from app.llm.provider import get_llm_client
from app.tools.contracts import ToolStatus
from app.tools.draft_email import draft_email
from app.tools.query_finops import query_finops_rag
from app.tools.review_invoice import review_invoice
from app.tools.search_vendors import search_vendors


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
    goal = state.get("goal") or ""
    sku = state.get("sku") or extract_sku(goal)
    quantity = state.get("quantity") or extract_quantity(goal)
    invoice_id = state.get("invoice_id") or extract_invoice_id(goal)
    bits = []
    if sku:
        bits.append(f"sku={sku}")
    if quantity:
        bits.append(f"qty={quantity}")
    if invoice_id:
        bits.append(f"invoice={invoice_id}")
    detail = ", ".join(bits) if bits else "no SKU/qty detected"
    return {
        "sku": sku,
        "quantity": quantity,
        "invoice_id": invoice_id,
        "original_sku": sku,
        "messages": [f"parse_goal: {detail}"],
        "trace": _trace(
            "parse_goal",
            f"Parsed goal → {detail}.",
            kind="thought",
            data={"sku": sku, "quantity": quantity, "invoice_id": invoice_id},
        ),
    }


def route_after_parse(
    state: ProcurementState,
) -> Literal["review_invoice", "search_vendors"]:
    """Invoice-only goals skip vendor search."""
    if state.get("invoice_id") and not state.get("quantity"):
        return "review_invoice"
    return "search_vendors"


def review_invoice_node(state: ProcurementState) -> dict[str, Any]:
    invoice_id = state.get("invoice_id")
    if not invoice_id:
        return {
            "messages": ["review_invoice: skipped"],
            "trace": _trace(
                "review_invoice",
                "Skipped review_invoice — no invoice_id.",
                kind="observation",
            ),
        }

    result = review_invoice(invoice_id=invoice_id)
    data = result.data.model_dump() if result.data else None
    return {
        "review_result": data,
        "hitl_status": "skipped",
        "messages": [f"review_invoice: {result.status.value}"],
        "trace": _trace(
            "review_invoice",
            result.observation,
            kind="observation",
            data={"status": result.status.value, "recommendation": (data or {}).get("recommendation")},
        ),
        "summary": result.observation,
    }


def search_vendors_node(state: ProcurementState) -> dict[str, Any]:
    sku = state.get("sku")
    quantity = state.get("quantity")
    attempts = int(state.get("search_attempts") or 0) + 1
    include_alternates = bool(state.get("replan_done"))

    if not sku or not quantity:
        return {
            "search_attempts": attempts,
            "messages": ["search_vendors: skipped (missing sku/qty)"],
            "trace": _trace(
                "search_vendors",
                "Skipped search_vendors — need SKU and quantity.",
                kind="observation",
                data={"search_attempts": attempts},
            ),
            "error": state.get("error") or "Missing SKU or quantity for vendor search.",
        }

    result = search_vendors(
        sku=sku,
        quantity=int(quantity),
        include_alternates=include_alternates,
    )
    # One retry on hard tool failure
    if result.status == ToolStatus.ERROR:
        result = search_vendors(
            sku=sku,
            quantity=int(quantity),
            include_alternates=include_alternates,
        )

    offers = []
    if result.data and result.data.offers:
        offers = [o.model_dump() for o in result.data.offers]
    best = result.data.best_offer.model_dump() if result.data and result.data.best_offer else None
    update: dict[str, Any] = {
        "search_attempts": attempts,
        "vendors": offers,
        "messages": [f"search_vendors: {result.status.value} (attempt {attempts})"],
        "trace": _trace(
            "search_vendors",
            result.observation,
            kind="observation",
            data={
                "status": result.status.value,
                "offer_count": len(offers),
                "search_attempts": attempts,
                "sku": sku,
                "include_alternates": include_alternates,
            },
        ),
    }
    if best:
        update["best_vendor"] = best["vendor"]
        update["best_price"] = float(best["unit_price"])
    if result.status == ToolStatus.ERROR:
        update["error"] = result.error or result.observation
    return update


def route_after_search(
    state: ProcurementState,
) -> Literal["replan_sku", "query_finops", "finalize"]:
    vendors = state.get("vendors") or []
    if vendors:
        return "query_finops"
    if state.get("sku") and state.get("quantity") and not state.get("replan_done"):
        return "replan_sku"
    # Still empty after replan (or missing inputs) — wrap up
    return "finalize"


def replan_sku_node(state: ProcurementState) -> dict[str, Any]:
    original = state.get("original_sku") or state.get("sku")
    suggested = suggest_similar_sku(original)
    if not suggested:
        return {
            "replan_done": True,
            "messages": ["replan_sku: no alternate SKU found"],
            "error": state.get("error") or f"No vendors for {original}; no alternate SKU.",
            "trace": _trace(
                "replan_sku",
                f"No similar SKU found for {original}.",
                kind="thought",
            ),
        }
    return {
        "sku": suggested,
        "suggested_sku": suggested,
        "replan_done": True,
        "messages": [f"replan_sku: {original} → {suggested}"],
        "error": None,
        "trace": _trace(
            "replan_sku",
            f"No vendors for {original}; re-planning with similar SKU {suggested}.",
            kind="thought",
            data={"original_sku": original, "suggested_sku": suggested},
        ),
    }


def query_finops_node(state: ProcurementState) -> dict[str, Any]:
    sku = state.get("sku")
    if sku:
        question = (
            f"What is the historical unit price and contract price for {sku}?"
        )
    else:
        question = state.get("goal") or "Summarize recent vendor spend."

    result = query_finops_rag(question=question, sku=sku)
    degraded = False
    if result.status == ToolStatus.ERROR:
        # Retry once, then degrade to empty facts
        result = query_finops_rag(question=question, sku=sku)
        if result.status == ToolStatus.ERROR:
            degraded = True

    update: dict[str, Any] = {
        "finops_degraded": degraded or bool(state.get("finops_degraded")),
        "messages": [
            f"query_finops: {'degraded' if degraded else result.status.value}"
        ],
        "trace": _trace(
            "query_finops",
            (
                f"FinOps failed after retry; continuing without history. ({result.error})"
                if degraded
                else result.observation
            ),
            kind="observation",
            data={
                "status": result.status.value,
                "source": (result.data.source if result.data else None),
                "degraded": degraded,
            },
        ),
    }
    if result.data and not degraded:
        if result.data.historical_unit_price is not None:
            update["historical_price"] = float(result.data.historical_unit_price)
        if result.data.contract_unit_price is not None:
            update["contract_price"] = float(result.data.contract_unit_price)
    return update


def compare_offers_node(state: ProcurementState) -> dict[str, Any]:
    vendors = list(state.get("vendors") or [])
    best_vendor = state.get("best_vendor")
    best_price = state.get("best_price")
    historical = state.get("historical_price")
    contract = state.get("contract_price")
    benchmark = None
    for candidate in (contract, historical, best_price):
        if candidate is not None:
            benchmark = float(candidate) if benchmark is None else min(benchmark, float(candidate))

    negotiate_vendor = None
    negotiate_price = None
    alpha = next((v for v in vendors if str(v.get("vendor", "")).lower() == "alpha supplies"), None)
    if alpha is not None:
        alpha_price = float(alpha["unit_price"])
        if benchmark is None or alpha_price > benchmark + 1e-9:
            negotiate_vendor = "Alpha Supplies"
            negotiate_price = alpha_price

    if negotiate_vendor is None and best_vendor and best_price is not None:
        negotiate_vendor = best_vendor
        negotiate_price = float(best_price)

    target = benchmark
    msg = (
        f"Best={best_vendor} @ {best_price}; "
        f"history={historical}; negotiate={negotiate_vendor} @ {negotiate_price}; "
        f"target={target}"
    )
    return {
        "negotiate_vendor": negotiate_vendor,
        "negotiate_price": negotiate_price,
        "messages": [f"compare_offers: {msg}"],
        "trace": _trace(
            "compare_offers",
            msg,
            kind="thought",
            data={
                "best_vendor": best_vendor,
                "best_price": best_price,
                "historical_price": historical,
                "negotiate_vendor": negotiate_vendor,
                "negotiate_price": negotiate_price,
                "target_unit_price": target,
            },
        ),
    }


def draft_email_node(state: ProcurementState) -> dict[str, Any]:
    vendor = state.get("negotiate_vendor") or state.get("best_vendor")
    sku = state.get("sku")
    quantity = state.get("quantity")
    quoted = state.get("negotiate_price") or state.get("best_price")

    if not vendor or not sku or not quantity or quoted is None:
        return {
            "messages": ["draft_email: skipped (incomplete compare state)"],
            "email_draft": None,
            "trace": _trace(
                "draft_email",
                "Skipped draft_email — missing vendor/sku/qty/price.",
                kind="observation",
            ),
        }

    target = None
    for candidate in (state.get("contract_price"), state.get("historical_price"), state.get("best_price")):
        if candidate is not None:
            target = float(candidate) if target is None else min(target, float(candidate))

    context_parts = []
    if state.get("best_vendor") and state.get("best_price") is not None:
        context_parts.append(
            f"Best catalog offer: {state['best_vendor']} @ ${float(state['best_price']):.2f}."
        )
    if state.get("historical_price") is not None:
        context_parts.append(
            f"FinOps historical unit price: ${float(state['historical_price']):.2f}."
        )
    if state.get("contract_price") is not None:
        context_parts.append(
            f"Contract unit price: ${float(state['contract_price']):.2f}."
        )
    if state.get("suggested_sku"):
        context_parts.append(
            f"Re-planned from {state.get('original_sku')} to {state.get('suggested_sku')}."
        )

    result = draft_email(
        vendor=vendor,
        sku=sku,
        quantity=int(quantity),
        quoted_unit_price=float(quoted),
        target_unit_price=target,
        intent="negotiate_price",
        context=" ".join(context_parts),
        llm=get_llm_client(),
    )
    if result.status == ToolStatus.ERROR:
        result = draft_email(
            vendor=vendor,
            sku=sku,
            quantity=int(quantity),
            quoted_unit_price=float(quoted),
            target_unit_price=target,
            intent="negotiate_price",
            context=" ".join(context_parts),
            llm=get_llm_client(),
        )

    draft = None
    if result.data:
        draft = result.data.model_dump()
    return {
        "email_draft": draft,
        "messages": [f"draft_email: {result.status.value}"],
        "trace": _trace(
            "draft_email",
            result.observation,
            kind="observation",
            data={"status": result.status.value, "vendor": vendor},
        ),
    }


def hitl_gate_node(state: ProcurementState) -> dict[str, Any]:
    """Pause for human approval when an email draft exists."""
    from langgraph.types import interrupt

    from app.agent.hitl import apply_edited_draft, parse_hitl_resume
    from app.agent.outbox import write_outbox_email
    from app.tools.contracts import HitlDecision

    draft = state.get("email_draft")
    if not draft:
        return {
            "hitl_status": "skipped",
            "messages": ["hitl_gate: skipped"],
            "trace": _trace(
                "hitl_gate",
                "HITL gate: no draft — skipped.",
                kind="status",
                data={"hitl_status": "skipped", "has_draft": False},
            ),
        }

    # Surface draft to the caller; resume value becomes the return of interrupt()
    decision_raw = interrupt(
        {
            "type": "email_approval",
            "prompt": "Approve, edit, or reject this negotiation email before send.",
            "actions": ["approve", "edit", "reject"],
            "draft": draft,
            "vendor": draft.get("vendor"),
            "sku": state.get("sku"),
            "goal": state.get("goal"),
        }
    )
    resume = parse_hitl_resume(decision_raw)
    decision = resume.decision

    update: dict[str, Any] = {
        "hitl_decision": decision.value,
        "messages": [f"hitl_gate: {decision.value}"],
    }

    if decision == HitlDecision.REJECT:
        update["hitl_status"] = "rejected"
        update["trace"] = _trace(
            "hitl_gate",
            "HITL rejected — email will not be sent.",
            kind="status",
            data={"hitl_status": "rejected"},
        )
        return update

    if decision == HitlDecision.EDIT:
        edited = apply_edited_draft(draft, resume.edited_draft or "")
        update["email_draft"] = edited
        update["hitl_status"] = "edited"
        # Treat edit as approval of the revised draft for MVP outbox write
        path = write_outbox_email(
            draft=edited,
            goal=state.get("goal") or "",
            extra={"decision": "edit"},
        )
        update["outbox_path"] = str(path)
        update["trace"] = _trace(
            "hitl_gate",
            f"HITL edited draft saved to outbox: {path.name}",
            kind="status",
            data={"hitl_status": "edited", "outbox_path": str(path)},
        )
        return update

    # approve
    path = write_outbox_email(
        draft=draft,
        goal=state.get("goal") or "",
        extra={"decision": "approve"},
    )
    update["hitl_status"] = "approved"
    update["outbox_path"] = str(path)
    update["trace"] = _trace(
        "hitl_gate",
        f"HITL approved — wrote outbox {path.name} (no SMTP).",
        kind="status",
        data={"hitl_status": "approved", "outbox_path": str(path)},
    )
    return update


def finalize_node(state: ProcurementState) -> dict[str, Any]:
    if state.get("review_result"):
        rec = state["review_result"].get("recommendation")
        summary = (
            state.get("summary")
            or f"Invoice review {state.get('invoice_id')}: {rec}."
        )
        return {
            "summary": summary,
            "messages": ["finalize: review done"],
            "trace": _trace("finalize", summary, kind="status"),
        }

    parts = [
        f"Goal: {state.get('goal')}",
        f"SKU={state.get('sku')} qty={state.get('quantity')}",
        f"Best offer: {state.get('best_vendor')} @ {state.get('best_price')}",
        f"FinOps historical: {state.get('historical_price')}",
        f"Negotiate: {state.get('negotiate_vendor')} @ {state.get('negotiate_price')}",
        f"HITL: {state.get('hitl_status')}",
        f"search_attempts={state.get('search_attempts')}",
    ]
    if state.get("suggested_sku"):
        parts.append(f"replan: {state.get('original_sku')}→{state.get('suggested_sku')}")
    if state.get("email_draft"):
        parts.append(f"Draft subject: {state['email_draft'].get('subject')}")
    if state.get("outbox_path"):
        parts.append(f"Outbox: {state['outbox_path']}")
    if state.get("finops_degraded"):
        parts.append("FinOps degraded")
    if state.get("error"):
        parts.append(f"Error: {state['error']}")
    if not (state.get("vendors") or state.get("email_draft") or state.get("review_result")):
        parts.append("No viable vendors after search/replan.")
    summary = " | ".join(parts)
    return {
        "summary": summary,
        "messages": ["finalize: done"],
        "trace": _trace("finalize", summary, kind="status"),
    }
