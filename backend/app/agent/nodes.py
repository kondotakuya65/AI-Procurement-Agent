"""Procurement graph nodes — happy-path tool wiring (C2)."""

from __future__ import annotations

from typing import Any

from app.agent.parse import extract_invoice_id, extract_quantity, extract_sku
from app.agent.state import ProcurementState, TraceEvent
from app.llm.provider import get_llm_client
from app.tools.draft_email import draft_email
from app.tools.query_finops import query_finops_rag
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
        "messages": [f"parse_goal: {detail}"],
        "trace": _trace(
            "parse_goal",
            f"Parsed goal → {detail}.",
            kind="thought",
            data={"sku": sku, "quantity": quantity, "invoice_id": invoice_id},
        ),
    }


def search_vendors_node(state: ProcurementState) -> dict[str, Any]:
    sku = state.get("sku")
    quantity = state.get("quantity")
    if not sku or not quantity:
        return {
            "messages": ["search_vendors: skipped (missing sku/qty)"],
            "trace": _trace(
                "search_vendors",
                "Skipped search_vendors — need SKU and quantity.",
                kind="observation",
            ),
            "error": state.get("error") or "Missing SKU or quantity for vendor search.",
        }

    result = search_vendors(sku=sku, quantity=int(quantity))
    offers = []
    if result.data and result.data.offers:
        offers = [o.model_dump() for o in result.data.offers]
    best = result.data.best_offer.model_dump() if result.data and result.data.best_offer else None
    update: dict[str, Any] = {
        "vendors": offers,
        "messages": [f"search_vendors: {result.status.value}"],
        "trace": _trace(
            "search_vendors",
            result.observation,
            kind="observation",
            data={"status": result.status.value, "offer_count": len(offers)},
        ),
    }
    if best:
        update["best_vendor"] = best["vendor"]
        update["best_price"] = float(best["unit_price"])
    return update


def query_finops_node(state: ProcurementState) -> dict[str, Any]:
    sku = state.get("sku")
    if sku:
        question = (
            f"What is the historical unit price and contract price for {sku}?"
        )
    else:
        question = state.get("goal") or "Summarize recent vendor spend."

    result = query_finops_rag(question=question, sku=sku)
    update: dict[str, Any] = {
        "messages": [f"query_finops: {result.status.value}"],
        "trace": _trace(
            "query_finops",
            result.observation,
            kind="observation",
            data={"status": result.status.value, "source": (result.data.source if result.data else None)},
        ),
    }
    if result.data:
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
    # Prefer negotiating with Alpha when they quote above benchmark / best competitor
    alpha = next((v for v in vendors if str(v.get("vendor", "")).lower() == "alpha supplies"), None)
    if alpha is not None:
        alpha_price = float(alpha["unit_price"])
        if benchmark is None or alpha_price > benchmark + 1e-9:
            negotiate_vendor = "Alpha Supplies"
            negotiate_price = alpha_price

    if negotiate_vendor is None and best_vendor and best_price is not None:
        # Fall back: negotiate with best offer toward historical/contract if higher
        if historical is not None and float(best_price) > float(historical):
            negotiate_vendor = best_vendor
            negotiate_price = float(best_price)
        else:
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
    """Gate before send — C4 adds interrupt() / resume."""
    has_draft = bool(state.get("email_draft"))
    status = state.get("hitl_status") or ("pending" if has_draft else "skipped")
    return {
        "hitl_status": status,
        "messages": [f"hitl_gate: {status}"],
        "trace": _trace(
            "hitl_gate",
            (
                "HITL gate: draft ready for Approve / Edit / Reject (interrupt in C4)."
                if has_draft
                else "HITL gate: no draft — skipped."
            ),
            kind="status",
            data={"hitl_status": status, "has_draft": has_draft},
        ),
    }


def finalize_node(state: ProcurementState) -> dict[str, Any]:
    parts = [
        f"Goal: {state.get('goal')}",
        f"SKU={state.get('sku')} qty={state.get('quantity')}",
        f"Best offer: {state.get('best_vendor')} @ {state.get('best_price')}",
        f"FinOps historical: {state.get('historical_price')}",
        f"Negotiate: {state.get('negotiate_vendor')} @ {state.get('negotiate_price')}",
        f"HITL: {state.get('hitl_status')}",
    ]
    if state.get("email_draft"):
        parts.append(f"Draft subject: {state['email_draft'].get('subject')}")
    if state.get("error"):
        parts.append(f"Error: {state['error']}")
    summary = " | ".join(parts)
    return {
        "summary": summary,
        "messages": ["finalize: done"],
        "trace": _trace("finalize", summary, kind="status"),
    }
