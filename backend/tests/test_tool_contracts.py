"""Tool contract validation tests."""

import pytest
from pydantic import ValidationError

from app.tools.contracts import (
    DraftEmailInput,
    HitlDecision,
    HitlResumeInput,
    QueryFinopsData,
    ReviewInvoiceData,
    ReviewRecommendation,
    SearchVendorsData,
    SearchVendorsInput,
    ToolName,
    ToolResult,
    ToolStatus,
    VendorOffer,
)


def test_search_vendors_input_requires_positive_qty():
    with pytest.raises(ValidationError):
        SearchVendorsInput(sku="SKU-1001", quantity=0)


def test_search_vendors_data_roundtrip():
    offer = VendorOffer(
        offer_id="OFF-1",
        vendor="Coastal Widgets",
        sku="SKU-1001",
        unit_price=9.95,
        available_qty=1500,
        moq=400,
        lead_days=14,
    )
    data = SearchVendorsData(
        sku="SKU-1001",
        quantity=500,
        offers=[offer],
        best_offer=offer,
    )
    result = ToolResult.ok(
        ToolName.SEARCH_VENDORS,
        data,
        observation="Found 1 offer; best Coastal Widgets @ $9.95",
    )
    dumped = result.model_dump()
    assert dumped["tool"] == "search_vendors"
    assert dumped["status"] == "ok"
    assert dumped["data"]["best_offer"]["unit_price"] == 9.95


def test_tool_result_empty_and_fail():
    empty = ToolResult.empty(
        ToolName.SEARCH_VENDORS,
        observation="No vendors for SKU-9999",
    )
    assert empty.status == ToolStatus.EMPTY
    assert empty.data is None

    failed = ToolResult.fail(ToolName.QUERY_FINOPS_RAG, "timeout")
    assert failed.status == ToolStatus.ERROR
    assert "timeout" in failed.observation


def test_tool_result_error_requires_message():
    with pytest.raises(ValidationError):
        ToolResult(
            tool=ToolName.DRAFT_EMAIL,
            status=ToolStatus.ERROR,
            observation="boom",
            error=None,
        )


def test_query_finops_data_facts():
    data = QueryFinopsData(
        answer="Historical price is $10.00",
        facts={"sku": "SKU-1001", "unit_price": 10.0},
        source="mock",
        historical_unit_price=10.0,
        contract_unit_price=10.0,
    )
    assert data.historical_unit_price == 10.0


def test_review_invoice_recommendation_enum():
    data = ReviewInvoiceData(
        invoice_id="INV-104",
        recommendation=ReviewRecommendation.REJECT,
        drift_pct=8.0,
        rationale="Over contract",
    )
    assert data.recommendation.value == "Reject"


def test_draft_email_input():
    inp = DraftEmailInput(
        vendor="Alpha Supplies",
        sku="SKU-1001",
        quantity=500,
        quoted_unit_price=10.8,
        target_unit_price=10.0,
        intent="negotiate_price",
    )
    assert inp.intent == "negotiate_price"


def test_hitl_edit_requires_draft():
    with pytest.raises(ValidationError):
        HitlResumeInput(decision=HitlDecision.EDIT, edited_draft=None)

    ok = HitlResumeInput(
        decision=HitlDecision.EDIT,
        edited_draft="Subject: Revised\n\nBody",
    )
    assert ok.decision == HitlDecision.EDIT


def test_hitl_approve_without_draft():
    payload = HitlResumeInput(decision=HitlDecision.APPROVE)
    assert payload.edited_draft is None


def test_tool_names_match_golden_scenario():
    expected = {
        "search_vendors",
        "query_finops_rag",
        "review_invoice",
        "draft_email",
    }
    assert {t.value for t in ToolName} == expected
