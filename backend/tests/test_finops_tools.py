"""FinOps tools: query_finops_rag + review_invoice."""

from __future__ import annotations

import httpx
import pytest

from app.config import clear_settings_cache
from app.tools.contracts import ReviewRecommendation, ToolStatus
from app.tools.finops_client import live_query, live_review, mock_query, query_with_mode
from app.tools.query_finops import query_finops_rag
from app.tools.review_invoice import review_invoice


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch):
    monkeypatch.setenv("FINOPS_MODE", "mock")
    clear_settings_cache()
    yield
    clear_settings_cache()


def test_query_finops_sku_price_mock():
    result = query_finops_rag(
        question="What is the historical unit price for SKU-1001?"
    )
    assert result.status == ToolStatus.OK
    assert result.data is not None
    assert result.data.source == "mock"
    assert result.data.historical_unit_price == 10.0
    assert "10.00" in result.data.answer or "10" in result.data.answer


def test_query_finops_alpha_q3_spend():
    result = query_finops_rag(question="How much did we spend on Vendor Alpha in Q3?")
    assert result.status == ToolStatus.OK
    assert result.data.facts.get("total_spend") == 10675.22


def test_query_finops_empty():
    result = query_finops_rag(question="Tell me about Martian widgets XYZ")
    assert result.status == ToolStatus.EMPTY


def test_review_inv_104_reject():
    result = review_invoice(invoice_id="INV-104")
    assert result.status == ToolStatus.OK
    assert result.data.recommendation == ReviewRecommendation.REJECT
    assert result.data.drift_pct == 8.0
    assert result.data.po_number == "PO-4452"


def test_review_inv_101_accept():
    result = review_invoice(invoice_id="INV-101")
    assert result.status == ToolStatus.OK
    assert result.data.recommendation == ReviewRecommendation.ACCEPT


def test_review_unknown_empty():
    result = review_invoice(invoice_id="INV-999")
    assert result.status == ToolStatus.EMPTY


def test_live_mode_falls_back_to_mock(monkeypatch):
    monkeypatch.setenv("FINOPS_MODE", "live")
    monkeypatch.setenv("FINOPS_API_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("FINOPS_RETRIES", "1")
    monkeypatch.setenv("FINOPS_TIMEOUT_SECONDS", "0.2")
    clear_settings_cache()

    raw = query_with_mode("historical unit price for SKU-1001")
    assert raw["source"] == "mock_fallback"
    assert raw.get("historical_unit_price") == 10.0


def test_live_query_success(monkeypatch):
    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "answer": "Live says $10",
                "facts": {"unit_price": 10.0, "contract_unit_price": 10.0},
            }

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url: str, json=None):
            assert url.endswith("/api/query")
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    out = live_query("price?")
    assert out["source"] == "live"
    assert out["historical_unit_price"] == 10.0


def test_live_review_success(monkeypatch):
    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "found": True,
                "invoice_id": "INV-104",
                "vendor": "Alpha Supplies",
                "po_number": "PO-4452",
                "po_match": True,
                "recommendation": "Reject",
                "summary": "Price drift 8%",
                "reasons": ["Unit price exceeds contract drift limit"],
                "alerts": [
                    {
                        "severity": "price_drift",
                        "sku": "SKU-1001",
                        "invoice_unit_price": 10.8,
                        "contract_unit_price": 10.0,
                        "drift_pct": 8.0,
                    }
                ],
                "contract": {"max_price_drift_pct": 5.0},
            }

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url: str, json=None):
            assert url.endswith("/api/review")
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    out = live_review("INV-104")
    assert out["source"] == "live"
    assert out["recommendation"] == "Reject"
    assert out["drift_pct"] == 8.0


def test_mock_query_with_sku_param():
    out = mock_query("any price question", sku="SKU-1001")
    assert out["historical_unit_price"] == 10.0
    assert out["empty"] is False
