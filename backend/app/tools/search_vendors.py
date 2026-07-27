"""search_vendors — fixture catalog search + price/lead ranking."""

from __future__ import annotations

import time

from app.fixtures import search_vendor_offers
from app.tools.contracts import (
    SearchVendorsData,
    SearchVendorsInput,
    ToolName,
    ToolResult,
    VendorOffer,
)


def search_vendors(
    inp: SearchVendorsInput | None = None,
    *,
    sku: str | None = None,
    quantity: int | None = None,
    include_alternates: bool = False,
) -> ToolResult[SearchVendorsData]:
    """Rank vendor offers for an SKU that can fulfill the requested quantity."""
    started = time.perf_counter()
    try:
        if inp is None:
            if sku is None or quantity is None:
                raise ValueError("sku and quantity are required")
            inp = SearchVendorsInput(
                sku=sku,
                quantity=quantity,
                include_alternates=include_alternates,
            )

        raw = search_vendor_offers(
            inp.sku,
            inp.quantity,
            include_alternates=inp.include_alternates,
        )
        offers = [VendorOffer.model_validate(row) for row in raw]
        best = offers[0] if offers else None
        data = SearchVendorsData(
            sku=inp.sku.strip().upper(),
            quantity=inp.quantity,
            offers=offers,
            best_offer=best,
        )
        latency_ms = (time.perf_counter() - started) * 1000

        if not offers:
            hint = (
                " Try include_alternates=true or a similar SKU."
                if not inp.include_alternates
                else ""
            )
            return ToolResult.empty(
                ToolName.SEARCH_VENDORS,
                observation=(
                    f"No vendors for {data.sku} qty {data.quantity}.{hint}"
                ),
                data=data,
                latency_ms=latency_ms,
            )

        observation = (
            f"Found {len(offers)} offer(s) for {data.sku} qty {data.quantity}; "
            f"best {best.vendor} @ ${best.unit_price:.2f} "
            f"(lead {best.lead_days}d)."
        )
        return ToolResult.ok(
            ToolName.SEARCH_VENDORS,
            data,
            observation=observation,
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001 — surface as ToolResult for the agent
        latency_ms = (time.perf_counter() - started) * 1000
        return ToolResult.fail(
            ToolName.SEARCH_VENDORS,
            str(exc),
            latency_ms=latency_ms,
        )
