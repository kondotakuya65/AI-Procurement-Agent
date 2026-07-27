"""Compile the procurement LangGraph (skeleton)."""

from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import ProcurementState

NODE_ORDER = (
    "parse_goal",
    "search_vendors",
    "query_finops",
    "compare_offers",
    "draft_email",
    "hitl_gate",
    "finalize",
)


def build_procurement_graph() -> StateGraph:
    graph = StateGraph(ProcurementState)
    graph.add_node("parse_goal", nodes.parse_goal)
    graph.add_node("search_vendors", nodes.search_vendors_node)
    graph.add_node("query_finops", nodes.query_finops_node)
    graph.add_node("compare_offers", nodes.compare_offers_node)
    graph.add_node("draft_email", nodes.draft_email_node)
    graph.add_node("hitl_gate", nodes.hitl_gate_node)
    graph.add_node("finalize", nodes.finalize_node)

    graph.add_edge(START, "parse_goal")
    graph.add_edge("parse_goal", "search_vendors")
    graph.add_edge("search_vendors", "query_finops")
    graph.add_edge("query_finops", "compare_offers")
    graph.add_edge("compare_offers", "draft_email")
    graph.add_edge("draft_email", "hitl_gate")
    graph.add_edge("hitl_gate", "finalize")
    graph.add_edge("finalize", END)
    return graph


def compile_procurement_graph(*, checkpointer: MemorySaver | None = None):
    """Compile with an in-memory checkpointer (required for later HITL)."""
    saver = checkpointer if checkpointer is not None else MemorySaver()
    return build_procurement_graph().compile(checkpointer=saver)


@lru_cache
def get_compiled_graph():
    return compile_procurement_graph()


def clear_graph_cache() -> None:
    get_compiled_graph.cache_clear()
