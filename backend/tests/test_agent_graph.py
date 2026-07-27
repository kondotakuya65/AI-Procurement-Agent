"""LangGraph skeleton tests."""

from app.agent.graph import NODE_ORDER, compile_procurement_graph
from app.agent.state import initial_state


def test_compiled_graph_runs_skeleton():
    graph = compile_procurement_graph()
    result = graph.invoke(
        initial_state(
            "Find a cost-effective vendor for 500 units of SKU-1001 "
            "and draft a negotiation email."
        ),
        config={"configurable": {"thread_id": "skeleton-1"}},
    )
    assert result["goal"].startswith("Find a cost-effective")
    assert result["email_draft"] is not None
    assert result["hitl_status"] == "pending"
    assert "Skeleton run complete" in (result.get("summary") or "")
    nodes_seen = [t["node"] for t in result["trace"]]
    assert nodes_seen == list(NODE_ORDER)


def test_node_order_constant():
    assert NODE_ORDER[0] == "parse_goal"
    assert NODE_ORDER[-1] == "finalize"
    assert "hitl_gate" in NODE_ORDER


def test_trace_reducer_appends():
    graph = compile_procurement_graph()
    result = graph.invoke(
        initial_state("Procure SKU-1001"),
        config={"configurable": {"thread_id": "skeleton-2"}},
    )
    assert len(result["trace"]) == len(NODE_ORDER)
    assert len(result["messages"]) == len(NODE_ORDER)
