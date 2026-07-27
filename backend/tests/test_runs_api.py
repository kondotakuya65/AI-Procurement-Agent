"""Runs API tests."""

from __future__ import annotations

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


def test_create_run_awaits_hitl(client: TestClient):
    res = client.post(
        "/api/runs",
        json={
            "goal": (
                "Find a cost-effective vendor for 500 units of SKU-1001 "
                "and draft a negotiation email."
            )
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "awaiting_hitl"
    assert body["interrupt"]["type"] == "email_approval"
    assert body["state"]["best_vendor"] == "Coastal Widgets"
    assert body["state"]["negotiate_vendor"] == "Alpha Supplies"
    assert body["state"]["email_draft"] is not None


def test_get_run_and_resume_approve(client: TestClient):
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

    got = client.get(f"/api/runs/{run_id}")
    assert got.status_code == 200
    assert got.json()["status"] == "awaiting_hitl"

    resumed = client.post(
        f"/api/runs/{run_id}/resume",
        json={"decision": "approve"},
    )
    assert resumed.status_code == 200
    body = resumed.json()
    assert body["status"] == "completed"
    assert body["interrupt"] is None
    assert body["state"]["hitl_status"] == "approved"
    assert body["state"]["outbox_path"]


def test_resume_reject(client: TestClient):
    run_id = client.post(
        "/api/runs",
        json={
            "goal": (
                "Find a cost-effective vendor for 500 units of SKU-1001 "
                "and draft a negotiation email."
            )
        },
    ).json()["run_id"]

    body = client.post(
        f"/api/runs/{run_id}/resume",
        json={"decision": "reject"},
    ).json()
    assert body["status"] == "completed"
    assert body["state"]["hitl_status"] == "rejected"
    assert not body["state"].get("outbox_path")


def test_invoice_review_completes_without_hitl(client: TestClient):
    body = client.post(
        "/api/runs",
        json={
            "goal": "Should we accept INV-104 against the Alpha contract and PO-4452?"
        },
    ).json()
    assert body["status"] == "completed"
    assert body["interrupt"] is None
    assert body["state"]["review_result"]["recommendation"] == "Reject"


def test_get_unknown_run_404(client: TestClient):
    res = client.get("/api/runs/does-not-exist")
    assert res.status_code == 404


def test_resume_completed_conflict(client: TestClient):
    run_id = client.post(
        "/api/runs",
        json={"goal": "Should we accept INV-104 against PO-4452?"},
    ).json()["run_id"]
    res = client.post(
        f"/api/runs/{run_id}/resume",
        json={"decision": "approve"},
    )
    assert res.status_code == 409
