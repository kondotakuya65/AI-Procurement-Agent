"""review_invoice tool — live FinOps HTTP or fixture mock."""

from __future__ import annotations

import time

from app.tools.contracts import (
    ReviewInvoiceData,
    ReviewInvoiceInput,
    ReviewRecommendation,
    ToolName,
    ToolResult,
)
from app.tools.finops_client import review_with_mode


def review_invoice(
    inp: ReviewInvoiceInput | None = None,
    *,
    invoice_id: str | None = None,
) -> ToolResult[ReviewInvoiceData]:
    started = time.perf_counter()
    try:
        if inp is None:
            if not invoice_id:
                raise ValueError("invoice_id is required")
            inp = ReviewInvoiceInput(invoice_id=invoice_id)

        raw = review_with_mode(inp.invoice_id)
        latency_ms = (time.perf_counter() - started) * 1000
        inv = str(raw.get("invoice_id") or inp.invoice_id).upper()
        rec_raw = str(raw.get("recommendation") or "Reject")
        recommendation = (
            ReviewRecommendation.ACCEPT
            if rec_raw.lower() == "accept"
            else ReviewRecommendation.REJECT
        )

        if not raw.get("found", False):
            data = ReviewInvoiceData(
                invoice_id=inv,
                recommendation=ReviewRecommendation.REJECT,
                rationale=str(raw.get("rationale") or "Invoice not found"),
            )
            return ToolResult.empty(
                ToolName.REVIEW_INVOICE,
                observation=f"FinOps review: {inv} not found.",
                data=data,
                latency_ms=latency_ms,
            )

        data = ReviewInvoiceData(
            invoice_id=inv,
            vendor=raw.get("vendor"),
            po_number=raw.get("po_number"),
            sku=raw.get("sku"),
            invoice_unit_price=raw.get("invoice_unit_price"),
            contract_unit_price=raw.get("contract_unit_price"),
            drift_pct=raw.get("drift_pct"),
            max_price_drift_pct=raw.get("max_price_drift_pct"),
            po_match=raw.get("po_match"),
            recommendation=recommendation,
            rationale=str(raw.get("rationale") or ""),
        )
        drift_bit = (
            f" drift {data.drift_pct:.1f}%."
            if data.drift_pct is not None
            else ""
        )
        return ToolResult.ok(
            ToolName.REVIEW_INVOICE,
            data,
            observation=(
                f"FinOps review {inv}: {data.recommendation.value}.{drift_bit} "
                f"{data.rationale[:120]}"
            ).strip(),
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - started) * 1000
        return ToolResult.fail(
            ToolName.REVIEW_INVOICE,
            str(exc),
            latency_ms=latency_ms,
        )
