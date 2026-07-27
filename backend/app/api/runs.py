"""HTTP API for procurement agent runs (+ SSE traces)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.runs import service
from app.tools.contracts import HitlResumeInput

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    goal: str = Field(
        ...,
        min_length=3,
        examples=[
            "Find a cost-effective vendor for 500 units of SKU-1001 and draft a negotiation email."
        ],
    )


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


def _sse_stream(events: Iterator[dict[str, Any]]) -> Iterator[str]:
    for event in events:
        yield _sse(event)


@router.post("")
def create_run(body: CreateRunRequest) -> dict:
    return service.create_run(body.goal)


@router.get("")
def list_runs(limit: int = 20) -> dict:
    return {"runs": service.list_runs(limit=limit)}


@router.post("/stream")
def create_run_stream(body: CreateRunRequest) -> StreamingResponse:
    """Create a run and stream thought/action/observation traces as SSE."""
    return StreamingResponse(
        _sse_stream(service.iter_create_run_events(body.goal)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}/stream")
def replay_run_stream(run_id: str) -> StreamingResponse:
    """Replay stored traces for a run (UI reconnect after POST /api/runs)."""
    return StreamingResponse(
        _sse_stream(service.iter_replay_run_events(run_id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{run_id}/resume/stream")
def resume_run_stream(run_id: str, body: HitlResumeInput) -> StreamingResponse:
    """Resume HITL and stream remaining node traces as SSE."""
    return StreamingResponse(
        _sse_stream(service.iter_resume_run_events(run_id, body)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    return service.get_run(run_id)


@router.post("/{run_id}/resume")
def resume_run(run_id: str, body: HitlResumeInput) -> dict:
    return service.resume_run(run_id, body)
