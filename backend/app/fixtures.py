"""Load procurement fixtures from FIXTURES_DIR."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings


def fixtures_root() -> Path:
    return Path(get_settings().fixtures_dir).resolve()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_vendor_catalog() -> dict[str, Any]:
    return _read_json(fixtures_root() / "vendors" / "catalog.json")


@lru_cache
def load_historical_prices() -> dict[str, Any]:
    return _read_json(fixtures_root() / "finops_mock" / "historical_prices.json")


@lru_cache
def load_review_cases() -> dict[str, Any]:
    return _read_json(fixtures_root() / "finops_mock" / "review_cases.json")


@lru_cache
def load_golden_scenarios() -> dict[str, Any]:
    return _read_json(fixtures_root() / "scenarios" / "golden.json")


def clear_fixture_caches() -> None:
    load_vendor_catalog.cache_clear()
    load_historical_prices.cache_clear()
    load_review_cases.cache_clear()
    load_golden_scenarios.cache_clear()


def search_vendor_offers(
    sku: str,
    quantity: int | None = None,
    *,
    include_alternates: bool = False,
) -> list[dict[str, Any]]:
    """Return ranked offers for an SKU (price asc, then lead_days)."""
    sku_u = sku.strip().upper()
    offers = list(load_vendor_catalog().get("offers", []))
    matched: list[dict[str, Any]] = []
    for offer in offers:
        offer_sku = str(offer.get("sku", "")).upper()
        if offer_sku == sku_u:
            matched.append(offer)
        elif include_alternates and (
            offer_sku.startswith(f"{sku_u}-") or offer_sku.endswith("-ALT")
        ):
            matched.append(offer)

    if quantity is not None:
        matched = [
            o
            for o in matched
            if int(o.get("moq", 0)) <= quantity
            and int(o.get("available_qty", 0)) >= quantity
        ]

    return sorted(
        matched,
        key=lambda o: (float(o["unit_price"]), int(o.get("lead_days", 999))),
    )


def get_sku_history(sku: str) -> dict[str, Any] | None:
    sku_u = sku.strip().upper()
    for row in load_historical_prices().get("sku_history", []):
        if str(row.get("sku", "")).upper() == sku_u:
            return row
    return None


def get_review_case(invoice_id: str) -> dict[str, Any] | None:
    inv = invoice_id.strip().upper()
    for case in load_review_cases().get("cases", []):
        if str(case.get("invoice_id", "")).upper() == inv:
            return case
    return None


def get_golden_scenario(scenario_id: str) -> dict[str, Any] | None:
    for sc in load_golden_scenarios().get("scenarios", []):
        if sc.get("id") == scenario_id:
            return sc
    return None
