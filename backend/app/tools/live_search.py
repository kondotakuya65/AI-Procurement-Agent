"""Optional live / hybrid vendor search (stretch).

Modes (VENDOR_SEARCH_MODE):
- fixtures — catalog only (default, deterministic demos/CI)
- live — live URL or simulated live overlay only
- hybrid — merge fixtures + live, re-rank by price/lead

Real web crawl/SerpAPI is intentionally not required; point VENDOR_LIVE_URL
at any HTTP API that returns ``{"offers": [...]}`` to plug in a live source.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.fixtures import fixtures_root, search_vendor_offers


@lru_cache
def load_live_overlay() -> dict[str, Any]:
    path = fixtures_root() / "vendors" / "live_overlay.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def clear_live_overlay_cache() -> None:
    load_live_overlay.cache_clear()


def _filter_offers(
    offers: list[dict[str, Any]],
    sku: str,
    quantity: int,
    *,
    include_alternates: bool,
) -> list[dict[str, Any]]:
    sku_u = sku.strip().upper()
    matched: list[dict[str, Any]] = []
    for offer in offers:
        offer_sku = str(offer.get("sku", "")).upper()
        if offer_sku == sku_u:
            matched.append(offer)
        elif include_alternates and (
            offer_sku.startswith(f"{sku_u}-") or offer_sku.endswith("-ALT")
        ):
            matched.append(offer)
    return [
        o
        for o in matched
        if int(o.get("moq", 0)) <= quantity
        and int(o.get("available_qty", 0)) >= quantity
    ]


def _rank(offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        offers,
        key=lambda o: (float(o["unit_price"]), int(o.get("lead_days", 999))),
    )


def fetch_live_url_offers(
    sku: str,
    quantity: int,
    *,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    url = (settings.vendor_live_url or "").strip()
    if not url:
        return []
    with httpx.Client(timeout=settings.finops_timeout_seconds) as client:
        res = client.get(url, params={"sku": sku, "quantity": quantity})
        res.raise_for_status()
        payload = res.json()
    offers = payload.get("offers") if isinstance(payload, dict) else payload
    if not isinstance(offers, list):
        return []
    return [o for o in offers if isinstance(o, dict)]


def simulated_live_offers(
    sku: str,
    quantity: int,
    *,
    include_alternates: bool = False,
) -> list[dict[str, Any]]:
    raw = list(load_live_overlay().get("offers") or [])
    return _rank(_filter_offers(raw, sku, quantity, include_alternates=include_alternates))


def collect_live_offers(
    sku: str,
    quantity: int,
    *,
    include_alternates: bool = False,
    settings: Settings | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Return (offers, source_label). Prefers VENDOR_LIVE_URL, else overlay."""
    settings = settings or get_settings()
    if (settings.vendor_live_url or "").strip():
        try:
            remote = fetch_live_url_offers(sku, quantity, settings=settings)
            filtered = _rank(
                _filter_offers(
                    remote, sku, quantity, include_alternates=include_alternates
                )
            )
            if filtered:
                return filtered, "live_url"
        except Exception:
            pass
    return (
        simulated_live_offers(
            sku, quantity, include_alternates=include_alternates
        ),
        "live_sim",
    )


def resolve_vendor_offers(
    sku: str,
    quantity: int,
    *,
    include_alternates: bool = False,
    settings: Settings | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Apply VENDOR_SEARCH_MODE and return ranked offers + source tag."""
    settings = settings or get_settings()
    mode = (settings.vendor_search_mode or "fixtures").strip().lower()

    fixture_offers = search_vendor_offers(
        sku, quantity, include_alternates=include_alternates
    )

    if mode in {"", "fixtures", "fixture", "catalog"}:
        return fixture_offers, "fixtures"

    live_offers, live_label = collect_live_offers(
        sku,
        quantity,
        include_alternates=include_alternates,
        settings=settings,
    )

    if mode == "live":
        return live_offers, live_label

    if mode == "hybrid":
        # Dedupe by offer_id then vendor+sku+price
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for offer in list(fixture_offers) + list(live_offers):
            key = str(
                offer.get("offer_id")
                or f"{offer.get('vendor')}|{offer.get('sku')}|{offer.get('unit_price')}"
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(offer)
        return _rank(merged), f"hybrid:{live_label}"

    raise ValueError(
        f"Unsupported VENDOR_SEARCH_MODE: {settings.vendor_search_mode!r} "
        "(use fixtures|live|hybrid)"
    )


def probe_finops(settings: Settings | None = None) -> dict[str, Any]:
    """Lightweight compose check against FinOps-RAG /health."""
    settings = settings or get_settings()
    base = settings.finops_api_url.rstrip("/")
    mode = settings.finops_mode.lower()
    result: dict[str, Any] = {
        "mode": mode,
        "api_url": base,
        "reachable": False,
        "detail": None,
    }
    if mode != "live":
        result["detail"] = "FINOPS_MODE is not live (using mock fixtures)."
        return result
    try:
        with httpx.Client(timeout=min(5.0, settings.finops_timeout_seconds)) as client:
            res = client.get(f"{base}/api/health")
            res.raise_for_status()
            body = res.json()
        result["reachable"] = True
        result["detail"] = body.get("service") or "ok"
        result["finops_health"] = body
    except Exception as exc:  # noqa: BLE001
        result["detail"] = str(exc)
    return result
