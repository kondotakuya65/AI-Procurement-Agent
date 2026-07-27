"""Happy-path LangGraph + parse tests."""

from app.agent.graph import NODE_ORDER, compile_procurement_graph
from app.agent.parse import extract_invoice_id, extract_quantity, extract_sku
from app.agent.state import initial_state
from app.config import clear_settings_cache


def test_extract_sku_qty_invoice():
    goal = "Find a cost-effective vendor for 500 units of SKU-1001 and draft email."
    assert extract_sku(goal) == "SKU-1001"
    assert extract_quantity(goal) == 500
    assert extract_invoice_id("Should we accept INV-104?") == "INV-104"


def test_happy_path_sku_1001(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    clear_settings_cache()

    graph = compile_procurement_graph()
    goal = (
        "Find a cost-effective vendor for 500 units of SKU-1001 "
        "and draft a negotiation email."
    )
    result = graph.invoke(
        initial_state(goal),
        config={"configurable": {"thread_id": "happy-1"}},
    )

    assert result["sku"] == "SKU-1001"
    assert result["quantity"] == 500
    assert result["best_vendor"] == "Coastal Widgets"
    assert result["best_price"] == 9.95
    assert result["historical_price"] == 10.0
    assert result["negotiate_vendor"] == "Alpha Supplies"
    assert result["negotiate_price"] == 10.8
    assert result["email_draft"] is not None
    assert "Alpha Supplies" in result["email_draft"]["body"]
    assert result["hitl_status"] == "pending"
    assert "Coastal Widgets" in (result.get("summary") or "")

    nodes_seen = [t["node"] for t in result["trace"]]
    # Every skeleton node appears at least once, in order
    positions = [nodes_seen.index(n) for n in NODE_ORDER]
    assert positions == sorted(positions)


def test_node_order_constant():
    assert NODE_ORDER[0] == "parse_goal"
    assert NODE_ORDER[-1] == "finalize"
    assert "hitl_gate" in NODE_ORDER


def test_missing_qty_skips_search(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    clear_settings_cache()

    graph = compile_procurement_graph()
    result = graph.invoke(
        initial_state("Tell me about SKU-1001 pricing history only"),
        config={"configurable": {"thread_id": "happy-2"}},
    )
    assert result["sku"] == "SKU-1001"
    assert result["quantity"] is None
    assert result["vendors"] == []
    assert result["email_draft"] is None
