"""Goal parsing helpers for the procurement graph."""

from __future__ import annotations

import re

_SKU_RE = re.compile(r"\bSKU[- ]?([A-Z0-9-]+)\b", re.I)
_QTY_RE = re.compile(
    r"\b(\d[\d,]*)\s*(?:units?|pcs|pieces|qty)\b|\b(?:qty|quantity)\s*[:=]?\s*(\d[\d,]*)\b",
    re.I,
)
_INV_RE = re.compile(r"\bINV[- ]?(\d+)\b", re.I)


def extract_sku(goal: str) -> str | None:
    m = _SKU_RE.search(goal or "")
    if not m:
        return None
    return f"SKU-{m.group(1).upper().lstrip('-')}"


def extract_quantity(goal: str) -> int | None:
    m = _QTY_RE.search(goal or "")
    if not m:
        return None
    raw = m.group(1) or m.group(2)
    return int(raw.replace(",", ""))


def extract_invoice_id(goal: str) -> str | None:
    m = _INV_RE.search(goal or "")
    if not m:
        return None
    return f"INV-{m.group(1)}"
