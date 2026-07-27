"""query_finops_rag tool — live FinOps HTTP or fixture mock."""

from __future__ import annotations

import time

from app.tools.contracts import (
    QueryFinopsData,
    QueryFinopsInput,
    ToolName,
    ToolResult,
)
from app.tools.finops_client import query_with_mode


def query_finops_rag(
    inp: QueryFinopsInput | None = None,
    *,
    question: str | None = None,
    sku: str | None = None,
    vendor: str | None = None,
) -> ToolResult[QueryFinopsData]:
    started = time.perf_counter()
    try:
        if inp is None:
            if not question:
                raise ValueError("question is required")
            inp = QueryFinopsInput(question=question, sku=sku, vendor=vendor)

        raw = query_with_mode(inp.question, sku=inp.sku, vendor=inp.vendor)
        data = QueryFinopsData(
            answer=str(raw.get("answer") or ""),
            facts=dict(raw.get("facts") or {}),
            source=str(raw.get("source") or "mock"),
            historical_unit_price=raw.get("historical_unit_price"),
            contract_unit_price=raw.get("contract_unit_price"),
        )
        latency_ms = (time.perf_counter() - started) * 1000

        if raw.get("empty"):
            return ToolResult.empty(
                ToolName.QUERY_FINOPS_RAG,
                observation=f"FinOps ({data.source}): no matching facts.",
                data=data,
                latency_ms=latency_ms,
            )

        price_bit = ""
        if data.historical_unit_price is not None:
            price_bit = f" Historical unit ${data.historical_unit_price:.2f}."
        return ToolResult.ok(
            ToolName.QUERY_FINOPS_RAG,
            data,
            observation=f"FinOps ({data.source}): {data.answer[:160]}{price_bit}",
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - started) * 1000
        return ToolResult.fail(
            ToolName.QUERY_FINOPS_RAG,
            str(exc),
            latency_ms=latency_ms,
        )
