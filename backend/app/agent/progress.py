"""Emit live progress events during graph/tool execution (SSE custom stream)."""

from __future__ import annotations

from typing import Any


def emit_progress(
    message: str,
    *,
    node: str | None = None,
    phase: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Best-effort custom stream event for the UI (no-op outside astream/stream)."""
    try:
        from langgraph.config import get_stream_writer

        writer = get_stream_writer()
    except Exception:
        return
    payload: dict[str, Any] = {
        "type": "progress",
        "message": message,
    }
    if node:
        payload["node"] = node
    if phase:
        payload["phase"] = phase
    if data:
        payload["data"] = data
    try:
        writer(payload)
    except Exception:
        return
