"""Suggest alternate SKUs when catalog search is empty."""

from __future__ import annotations

from app.fixtures import load_vendor_catalog


def suggest_similar_sku(sku: str | None) -> str | None:
    """Pick a near substitute from the vendor catalog.

    Preference order:
    1. ``{sku}-ALT`` if present
    2. Any catalog SKU ending in ``-ALT``
    3. ``None`` if nothing useful
    """
    offers = load_vendor_catalog().get("offers", [])
    skus = {str(o.get("sku", "")).upper() for o in offers}
    if sku:
        candidate = f"{sku.strip().upper()}-ALT"
        if candidate in skus:
            return candidate
    alts = sorted(s for s in skus if s.endswith("-ALT"))
    return alts[0] if alts else None
