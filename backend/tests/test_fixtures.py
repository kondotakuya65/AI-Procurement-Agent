"""Fixture loading and demo-number sanity checks."""

from app.fixtures import (
    get_review_case,
    get_sku_history,
    get_golden_scenario,
    search_vendor_offers,
)


def test_vendor_catalog_ranks_coastal_for_sku_1001():
    offers = search_vendor_offers("SKU-1001", quantity=500)
    assert len(offers) >= 3
    assert offers[0]["vendor"] == "Coastal Widgets"
    assert offers[0]["unit_price"] == 9.95
    vendors = {o["vendor"] for o in offers}
    assert "Alpha Supplies" in vendors
    alpha = next(o for o in offers if o["vendor"] == "Alpha Supplies")
    assert alpha["unit_price"] == 10.8


def test_sku_1001_history_matches_finops_contract():
    hist = get_sku_history("SKU-1001")
    assert hist is not None
    assert hist["contract_unit_price"] == 10.0
    assert hist["last_paid_unit_price"] == 10.0
    assert hist["avg_paid_unit_price"] == 10.0


def test_alpha_q3_spend_anchor():
    from app.fixtures import load_historical_prices

    spend = load_historical_prices()["vendor_spend"]
    alpha = next(s for s in spend if s["vendor"] == "Alpha Supplies")
    assert alpha["total_spend"] == 10675.22
    assert alpha["period"] == "2024-Q3"


def test_inv_104_review_is_reject():
    case = get_review_case("INV-104")
    assert case is not None
    assert case["recommendation"] == "Reject"
    assert case["drift_pct"] == 8.0
    assert case["po_number"] == "PO-4452"


def test_inv_101_review_is_accept():
    case = get_review_case("INV-101")
    assert case is not None
    assert case["recommendation"] == "Accept"


def test_unknown_sku_empty_exact_but_alt_exists():
    exact = search_vendor_offers("SKU-9999", quantity=100)
    assert exact == []
    alts = search_vendor_offers("SKU-1001", include_alternates=True)
    alt_skus = {o["sku"] for o in alts}
    assert "SKU-1001-ALT" in alt_skus


def test_golden_happy_path_expectations():
    sc = get_golden_scenario("happy_path_sku_1001")
    assert sc is not None
    assert sc["expected_tool_order"][0] == "search_vendors"
    assert "draft_email" in sc["expected_tool_order"]
    assert sc["expected"]["best_vendor"] == "Coastal Widgets"
    assert sc["expected"]["historical_unit_price"] == 10.0
    assert sc["expected"]["hitl_required"] is True


def test_golden_scenarios_cover_replan_and_review():
    assert get_golden_scenario("zero_vendors_replan") is not None
    assert get_golden_scenario("price_drift_review_inv_104") is not None
    review = get_golden_scenario("price_drift_review_inv_104")
    assert review["expected"]["recommendation"] == "Reject"
