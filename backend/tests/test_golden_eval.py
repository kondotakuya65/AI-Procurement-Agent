"""Parametrized golden eval — mock LLM + mock FinOps."""

from __future__ import annotations

import pytest

from app.config import clear_settings_cache
from app.eval.runner import run_all_golden, run_golden_scenario
from app.fixtures import load_golden_scenarios
from app.runs.service import clear_runs


@pytest.fixture(autouse=True)
def _eval_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path / "outbox"))
    clear_settings_cache()
    clear_runs()
    yield
    clear_runs()
    clear_settings_cache()


def _scenario_ids() -> list[str]:
    return [s["id"] for s in load_golden_scenarios().get("scenarios") or []]


@pytest.mark.parametrize("scenario_id", _scenario_ids())
def test_golden_scenario(scenario_id: str):
    report = run_golden_scenario(scenario_id, thread_id=f"pytest-{scenario_id}")
    assert report["passed"], "; ".join(report["failures"])


def test_run_all_golden_summary():
    reports = run_all_golden()
    assert len(reports) == len(_scenario_ids())
    failed = [r["id"] for r in reports if not r["passed"]]
    assert failed == [], f"failed scenarios: {failed}"
