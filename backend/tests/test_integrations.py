"""Live / hybrid vendor search + FinOps compose probes."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import clear_settings_cache
from app.main import app
from app.tools.live_search import clear_live_overlay_cache, resolve_vendor_offers
from app.tools.search_vendors import search_vendors
from app.runs.service import clear_runs


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FINOPS_MODE", "mock")
    monkeypatch.setenv("VENDOR_SEARCH_MODE", "fixtures")
    monkeypatch.setenv("VENDOR_LIVE_URL", "")
    clear_settings_cache()
    clear_live_overlay_cache()
    clear_runs()
    yield
    clear_settings_cache()
    clear_live_overlay_cache()
    clear_runs()


def test_fixtures_mode_ranks_coastal(monkeypatch):
    monkeypatch.setenv("VENDOR_SEARCH_MODE", "fixtures")
    clear_settings_cache()
    result = search_vendors(sku="SKU-1001", quantity=500)
    assert result.data is not None
    assert result.data.source == "fixtures"
    assert result.data.best_offer.vendor == "Coastal Widgets"


def test_live_mode_uses_overlay(monkeypatch):
    monkeypatch.setenv("VENDOR_SEARCH_MODE", "live")
    clear_settings_cache()
    result = search_vendors(sku="SKU-1001", quantity=500)
    assert result.data is not None
    assert result.data.source == "live_sim"
    assert result.data.best_offer.vendor == "Orbit Industrial"
    assert result.data.best_offer.unit_price == 9.8
    assert "live_sim" in result.observation


def test_hybrid_merges_and_prefers_orbit(monkeypatch):
    monkeypatch.setenv("VENDOR_SEARCH_MODE", "hybrid")
    clear_settings_cache()
    offers, source = resolve_vendor_offers("SKU-1001", 500)
    assert source.startswith("hybrid:")
    vendors = {o["vendor"] for o in offers}
    assert "Coastal Widgets" in vendors
    assert "Orbit Industrial" in vendors
    assert offers[0]["vendor"] == "Orbit Industrial"

    result = search_vendors(sku="SKU-1001", quantity=500)
    assert result.data.best_offer.vendor == "Orbit Industrial"


def test_live_url_success(monkeypatch):
    monkeypatch.setenv("VENDOR_SEARCH_MODE", "live")
    monkeypatch.setenv("VENDOR_LIVE_URL", "http://vendors.example/search")
    clear_settings_cache()

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "offers": [
                    {
                        "offer_id": "REMOTE-1",
                        "vendor": "Remote Vendor",
                        "sku": "SKU-1001",
                        "unit_price": 9.5,
                        "moq": 100,
                        "available_qty": 9999,
                        "lead_days": 3,
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url: str, params=None):
            assert "vendors.example" in url
            assert params["sku"] == "SKU-1001"
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    result = search_vendors(sku="SKU-1001", quantity=500)
    assert result.data.source == "live_url"
    assert result.data.best_offer.vendor == "Remote Vendor"


def test_integrations_endpoint():
    client = TestClient(app)
    res = client.get("/api/integrations")
    assert res.status_code == 200
    body = res.json()
    assert body["vendor_search_mode"] == "fixtures"
    assert body["finops"]["mode"] == "mock"
    assert body["compose_ready"] is True
    assert body["ports"]["agent_api"] == 8100
    assert body["ports"]["finops_api"] == 8000


def test_health_includes_vendor_search_mode():
    client = TestClient(app)
    body = client.get("/api/health").json()
    assert "vendor_search_mode" in body
