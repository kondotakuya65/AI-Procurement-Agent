"""search_vendors tool tests."""

from app.tools.contracts import ToolStatus
from app.tools.search_vendors import search_vendors


def test_search_vendors_happy_path_ranks_coastal():
    result = search_vendors(sku="SKU-1001", quantity=500)
    assert result.status == ToolStatus.OK
    assert result.tool.value == "search_vendors"
    assert result.data is not None
    assert result.data.best_offer is not None
    assert result.data.best_offer.vendor == "Coastal Widgets"
    assert result.data.best_offer.unit_price == 9.95
    assert "Coastal Widgets" in result.observation
    assert result.latency_ms is not None


def test_search_vendors_includes_alpha_quote():
    result = search_vendors(sku="SKU-1001", quantity=500)
    vendors = {o.vendor for o in result.data.offers}
    assert "Alpha Supplies" in vendors
    alpha = next(o for o in result.data.offers if o.vendor == "Alpha Supplies")
    assert alpha.unit_price == 10.8


def test_search_vendors_unknown_sku_empty():
    result = search_vendors(sku="SKU-9999", quantity=100)
    assert result.status == ToolStatus.EMPTY
    assert result.data is not None
    assert result.data.offers == []
    assert result.data.best_offer is None
    assert "No vendors" in result.observation


def test_search_vendors_alternates_include_alt_sku():
    result = search_vendors(
        sku="SKU-1001",
        quantity=200,
        include_alternates=True,
    )
    assert result.status == ToolStatus.OK
    skus = {o.sku for o in result.data.offers}
    assert "SKU-1001-ALT" in skus


def test_search_vendors_filters_moq():
    # Coastal MOQ is 400; Nova MOQ is 250 — qty 100 excludes both
    result = search_vendors(sku="SKU-1001", quantity=100)
    assert result.status == ToolStatus.OK
    vendors = {o.vendor for o in result.data.offers}
    assert "Coastal Widgets" not in vendors
    assert "Nova Components" not in vendors
    assert result.data.best_offer.vendor == "Alpha Supplies"
    assert result.data.best_offer.unit_price == 10.8


def test_search_vendors_input_model():
    from app.tools.contracts import SearchVendorsInput

    result = search_vendors(SearchVendorsInput(sku="sku-1001", quantity=500))
    assert result.data.sku == "SKU-1001"
