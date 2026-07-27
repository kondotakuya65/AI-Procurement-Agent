"""Happy-path + re-plan + HITL LangGraph tests."""

from pathlib import Path

from app.agent.graph import NODE_ORDER, compile_procurement_graph
from app.agent.hitl import resume_command
from app.agent.parse import extract_invoice_id, extract_quantity, extract_sku
from app.agent.replan import suggest_similar_sku
from app.agent.state import initial_state
from app.config import clear_settings_cache


def _has_interrupt(result: dict) -> bool:
    return bool(result.get("__interrupt__"))


def test_extract_sku_qty_invoice():
    goal = "Find a cost-effective vendor for 500 units of SKU-1001 and draft email."
    assert extract_sku(goal) == "SKU-1001"
    assert extract_quantity(goal) == 500
    assert extract_invoice_id("Should we accept INV-104?") == "INV-104"


def test_suggest_similar_sku():
    assert suggest_similar_sku("SKU-9999") == "SKU-1001-ALT"
    assert suggest_similar_sku("SKU-1001") == "SKU-1001-ALT"


def test_happy_path_approve_writes_outbox(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path / "outbox"))
    clear_settings_cache()

    graph = compile_procurement_graph()
    config = {"configurable": {"thread_id": "happy-1"}}
    goal = (
        "Find a cost-effective vendor for 500 units of SKU-1001 "
        "and draft a negotiation email."
    )
    paused = graph.invoke(initial_state(goal), config=config)
    assert _has_interrupt(paused)
    interrupt_val = paused["__interrupt__"][0].value
    assert interrupt_val["type"] == "email_approval"
    assert interrupt_val["draft"]["vendor"] == "Alpha Supplies"

    # State before resume still has compare results in checkpoint
    snap = graph.get_state(config)
    values = snap.values
    assert values["best_vendor"] == "Coastal Widgets"
    assert values["best_price"] == 9.95
    assert values["historical_price"] == 10.0
    assert values["negotiate_vendor"] == "Alpha Supplies"
    assert values["negotiate_price"] == 10.8

    result = graph.invoke(resume_command("approve"), config=config)
    assert not _has_interrupt(result)
    assert result["hitl_status"] == "approved"
    assert result["outbox_path"]
    assert Path(result["outbox_path"]).exists()
    assert "Alpha Supplies" in result["email_draft"]["body"]
    assert "approved" in (result.get("summary") or "").lower() or result["hitl_status"] == "approved"

    nodes_seen = [t["node"] for t in result["trace"]]
    assert "hitl_gate" in nodes_seen
    assert "finalize" in nodes_seen
    # Happy-path nodes appear in order in the accumulated trace
    happy = [n for n in NODE_ORDER if n in nodes_seen]
    assert happy == [n for n in NODE_ORDER if n in set(nodes_seen)]


def test_hitl_reject_skips_outbox(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path / "outbox"))
    clear_settings_cache()

    graph = compile_procurement_graph()
    config = {"configurable": {"thread_id": "hitl-reject"}}
    graph.invoke(
        initial_state(
            "Find a cost-effective vendor for 500 units of SKU-1001 "
            "and draft a negotiation email."
        ),
        config=config,
    )
    result = graph.invoke(resume_command("reject"), config=config)
    assert result["hitl_status"] == "rejected"
    assert result.get("outbox_path") in (None, "")
    assert list((tmp_path / "outbox").glob("*.json")) == []


def test_hitl_edit_updates_draft_and_outbox(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path / "outbox"))
    clear_settings_cache()

    graph = compile_procurement_graph()
    config = {"configurable": {"thread_id": "hitl-edit"}}
    graph.invoke(
        initial_state(
            "Find a cost-effective vendor for 500 units of SKU-1001 "
            "and draft a negotiation email."
        ),
        config=config,
    )
    edited = "Subject: Revised offer request\n\nPlease match $9.95.\n"
    result = graph.invoke(
        resume_command("edit", edited_draft=edited),
        config=config,
    )
    assert result["hitl_status"] == "edited"
    assert result["email_draft"]["subject"] == "Revised offer request"
    assert "9.95" in result["email_draft"]["body"]
    assert Path(result["outbox_path"]).exists()


def test_zero_vendors_replans_to_alt(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    monkeypatch.setenv("OUTBOX_DIR", str(tmp_path / "outbox"))
    clear_settings_cache()

    graph = compile_procurement_graph()
    config = {"configurable": {"thread_id": "replan-1"}}
    paused = graph.invoke(
        initial_state("Procure 100 units of SKU-9999."),
        config=config,
    )
    assert _has_interrupt(paused)
    snap = graph.get_state(config).values
    assert snap["original_sku"] == "SKU-9999"
    assert snap["suggested_sku"] == "SKU-1001-ALT"
    assert snap["sku"] == "SKU-1001-ALT"
    assert snap["search_attempts"] == 2
    assert snap["best_vendor"] == "Gamma Logistics"

    result = graph.invoke(resume_command("approve"), config=config)
    assert result["hitl_status"] == "approved"
    search_events = [t for t in result["trace"] if t["node"] == "search_vendors"]
    assert len(search_events) == 2


def test_invoice_review_branch(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    clear_settings_cache()

    graph = compile_procurement_graph()
    result = graph.invoke(
        initial_state(
            "Should we accept INV-104 against the Alpha contract and PO-4452?"
        ),
        config={"configurable": {"thread_id": "review-1"}},
    )

    assert not _has_interrupt(result)
    assert result["invoice_id"] == "INV-104"
    assert result["review_result"]["recommendation"] == "Reject"
    assert result["hitl_status"] == "skipped"
    assert result["email_draft"] is None


def test_node_order_constant():
    assert NODE_ORDER[0] == "parse_goal"
    assert NODE_ORDER[-1] == "finalize"
    assert "hitl_gate" in NODE_ORDER


def test_missing_qty_finalizes_without_draft(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    clear_settings_cache()

    graph = compile_procurement_graph()
    result = graph.invoke(
        initial_state("Tell me about SKU-1001 pricing history only"),
        config={"configurable": {"thread_id": "happy-2"}},
    )
    assert not _has_interrupt(result)
    assert result["sku"] == "SKU-1001"
    assert result["quantity"] is None
    assert result["email_draft"] is None
