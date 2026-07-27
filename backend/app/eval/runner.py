"""Golden scenario eval runner (mock LLM / mock FinOps)."""

from __future__ import annotations

from typing import Any

from app.agent.graph import compile_procurement_graph
from app.agent.hitl import resume_command
from app.agent.state import initial_state
from app.fixtures import get_golden_scenario, load_golden_scenarios

# Graph node name → tool id used in golden expected_tool_order
_NODE_TO_TOOL = {
    "search_vendors": "search_vendors",
    "query_finops": "query_finops_rag",
    "draft_email": "draft_email",
    "review_invoice": "review_invoice",
}


def tool_order_from_trace(trace: list[dict[str, Any]]) -> list[str]:
    order: list[str] = []
    for event in trace:
        node = event.get("node")
        tool = _NODE_TO_TOOL.get(str(node))
        if tool:
            order.append(tool)
    return order


def _has_interrupt(result: dict[str, Any]) -> bool:
    return bool(result.get("__interrupt__"))


def run_golden_scenario(
    scenario_id: str,
    *,
    thread_id: str | None = None,
    auto_approve: bool = True,
) -> dict[str, Any]:
    """Execute one golden scenario and return a structured eval report."""
    scenario = get_golden_scenario(scenario_id)
    if not scenario:
        raise KeyError(f"Unknown golden scenario: {scenario_id}")

    graph = compile_procurement_graph()
    tid = thread_id or f"eval-{scenario_id}"
    config = {"configurable": {"thread_id": tid}}
    goal = scenario["goal"]

    paused = graph.invoke(initial_state(goal), config=config)
    interrupted = _has_interrupt(paused)
    values = graph.get_state(config).values
    final = values

    if interrupted and auto_approve and scenario.get("expected", {}).get("hitl_required"):
        final = graph.invoke(resume_command("approve"), config=config)
        if _has_interrupt(final):
            raise RuntimeError("Still interrupted after approve")
    elif interrupted and auto_approve and not scenario.get("expected", {}).get("hitl_required"):
        # Scenario didn't expect HITL but graph paused — still finish for summary
        final = graph.invoke(resume_command("approve"), config=config)

    # Prefer completed state; if still on interrupt snapshot, use checkpoint values
    if _has_interrupt(final):
        state = dict(graph.get_state(config).values)
    else:
        state = dict(final)

    trace = list(state.get("trace") or [])
    # Include traces accumulated before HITL if finalize replaced them... reducer appends, OK
    actual_tools = tool_order_from_trace(trace)
    expected_tools = list(scenario.get("expected_tool_order") or [])

    report = {
        "id": scenario_id,
        "goal": goal,
        "expected_tool_order": expected_tools,
        "actual_tool_order": actual_tools,
        "tool_order_ok": _prefix_or_equal(actual_tools, expected_tools),
        "interrupted_before_approve": interrupted,
        "state": {
            "sku": state.get("sku"),
            "quantity": state.get("quantity"),
            "best_vendor": state.get("best_vendor"),
            "best_price": state.get("best_price"),
            "historical_price": state.get("historical_price"),
            "negotiate_vendor": state.get("negotiate_vendor"),
            "negotiate_price": state.get("negotiate_price"),
            "suggested_sku": state.get("suggested_sku"),
            "search_attempts": state.get("search_attempts"),
            "hitl_status": state.get("hitl_status"),
            "review_result": state.get("review_result"),
            "email_draft": state.get("email_draft"),
            "outbox_path": state.get("outbox_path"),
        },
        "expected": scenario.get("expected") or {},
        "passed": False,
        "failures": [],
    }
    report["failures"] = _check_expectations(report)
    report["passed"] = len(report["failures"]) == 0
    return report


def _prefix_or_equal(actual: list[str], expected: list[str]) -> bool:
    """Actual tool sequence must contain expected as an ordered subsequence.

    Allows extra nodes between expected tools (e.g. replan_sku between searches)
    as long as expected tools appear in order.
    """
    if not expected:
        return True
    i = 0
    for tool in actual:
        if tool == expected[i]:
            i += 1
            if i == len(expected):
                return True
    return False


def _check_expectations(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    exp = report["expected"]
    state = report["state"]

    if not report["tool_order_ok"]:
        failures.append(
            f"tool_order expected subsequence {report['expected_tool_order']}, "
            f"got {report['actual_tool_order']}"
        )

    if "best_vendor" in exp and state.get("best_vendor") != exp["best_vendor"]:
        failures.append(
            f"best_vendor expected {exp['best_vendor']!r}, got {state.get('best_vendor')!r}"
        )
    if "best_unit_price" in exp:
        got = state.get("best_price")
        if got is None or abs(float(got) - float(exp["best_unit_price"])) > 1e-6:
            failures.append(
                f"best_unit_price expected {exp['best_unit_price']}, got {got}"
            )
    if "historical_unit_price" in exp:
        got = state.get("historical_price")
        if got is None or abs(float(got) - float(exp["historical_unit_price"])) > 1e-6:
            failures.append(
                f"historical_unit_price expected {exp['historical_unit_price']}, got {got}"
            )
    if "negotiate_with" in exp and state.get("negotiate_vendor") != exp["negotiate_with"]:
        failures.append(
            f"negotiate_with expected {exp['negotiate_with']!r}, "
            f"got {state.get('negotiate_vendor')!r}"
        )
    if "alpha_quote" in exp:
        got = state.get("negotiate_price")
        if got is None or abs(float(got) - float(exp["alpha_quote"])) > 1e-6:
            failures.append(f"alpha_quote expected {exp['alpha_quote']}, got {got}")

    if exp.get("first_search_empty"):
        attempts = int(state.get("search_attempts") or 0)
        if attempts < 2:
            failures.append(f"expected replan search_attempts>=2, got {attempts}")
    if "suggested_sku" in exp and state.get("suggested_sku") != exp["suggested_sku"]:
        failures.append(
            f"suggested_sku expected {exp['suggested_sku']!r}, "
            f"got {state.get('suggested_sku')!r}"
        )

    if "recommendation" in exp:
        review = state.get("review_result") or {}
        if review.get("recommendation") != exp["recommendation"]:
            failures.append(
                f"recommendation expected {exp['recommendation']!r}, "
                f"got {review.get('recommendation')!r}"
            )
    if "drift_pct" in exp:
        review = state.get("review_result") or {}
        got = review.get("drift_pct")
        if got is None or abs(float(got) - float(exp["drift_pct"])) > 1e-6:
            failures.append(f"drift_pct expected {exp['drift_pct']}, got {got}")
    if "invoice_id" in exp:
        review = state.get("review_result") or {}
        if review.get("invoice_id") != exp["invoice_id"]:
            failures.append(
                f"invoice_id expected {exp['invoice_id']!r}, got {review.get('invoice_id')!r}"
            )

    if exp.get("hitl_required") and not report["interrupted_before_approve"]:
        failures.append("expected HITL interrupt before approve")
    if exp.get("hitl_required") is False and report["interrupted_before_approve"]:
        # Soft: review path should not interrupt
        if report["id"] == "price_drift_review_inv_104":
            failures.append("review path should not interrupt for HITL")

    return failures


def run_all_golden() -> list[dict[str, Any]]:
    scenarios = load_golden_scenarios().get("scenarios") or []
    return [
        run_golden_scenario(sc["id"], thread_id=f"eval-all-{sc['id']}")
        for sc in scenarios
    ]
