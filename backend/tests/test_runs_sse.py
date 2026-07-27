"""SSE streaming tests for runs API."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import clear_settings_cache
from app.main import app
from app.runs.service import clear_runs


@pytest.fixture(autouse=True)
def _reset(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path / "outbox"))
    clear_settings_cache()
    clear_runs()
    yield
    clear_runs()
    clear_settings_cache()


@pytest.fixture()
def client():
    return TestClient(app)


def _parse_sse(text: str) -> list[dict]:
    events = []
    for block in text.split("\n\n"):
        line = block.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:") :].strip()
        if payload:
            events.append(json.loads(payload))
    return events


def test_create_run_stream_emits_traces_and_interrupt(client: TestClient):
    with client.stream(
        "POST",
        "/api/runs/stream",
        json={
            "goal": (
                "Find a cost-effective vendor for 500 units of SKU-1001 "
                "and draft a negotiation email."
            )
        },
    ) as res:
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        body = "".join(res.iter_text())

    events = _parse_sse(body)
    types = [e["type"] for e in events]
    assert types[0] == "status"
    assert "progress" in types
    assert "trace" in types
    assert "interrupt" in types
    assert types[-1] == "done"

    progress_msgs = [e.get("message", "") for e in events if e["type"] == "progress"]
    assert any("draft" in m.lower() or "llm" in m.lower() or "vendor" in m.lower() for m in progress_msgs)

    traces = [e for e in events if e["type"] == "trace"]
    nodes = [t["node"] for t in traces]
    assert "parse_goal" in nodes
    assert "search_vendors" in nodes
    assert "draft_email" in nodes
    assert any(t.get("kind") in {"thought", "action", "observation", "status"} for t in traces)

    done = events[-1]
    assert done["status"] == "awaiting_hitl"
    assert done["interrupt"]["type"] == "email_approval"
    run_id = done["run_id"]

    # Replay endpoint returns stored traces
    with client.stream("GET", f"/api/runs/{run_id}/stream") as replay:
        replay_events = _parse_sse("".join(replay.iter_text()))
    assert replay_events[0].get("replay") is True
    assert any(e["type"] == "trace" for e in replay_events)
    assert replay_events[-1]["type"] == "done"


def test_resume_stream_approve(client: TestClient):
    created = client.post(
        "/api/runs",
        json={
            "goal": (
                "Find a cost-effective vendor for 500 units of SKU-1001 "
                "and draft a negotiation email."
            )
        },
    ).json()
    run_id = created["run_id"]

    with client.stream(
        "POST",
        f"/api/runs/{run_id}/resume/stream",
        json={"decision": "approve"},
    ) as res:
        events = _parse_sse("".join(res.iter_text()))

    assert events[0]["type"] == "status"
    assert events[-1]["type"] == "done"
    assert events[-1]["status"] == "completed"
    assert events[-1]["state"]["hitl_status"] == "approved"
    assert any(e["type"] == "trace" for e in events)
