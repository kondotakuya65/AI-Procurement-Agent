"""FinOps HTTP client with fixture mock + live fallback."""

from __future__ import annotations

import re
import time
from typing import Any

import httpx

from app.config import Settings, get_settings
from app.fixtures import get_review_case, get_sku_history, load_historical_prices

_SKU_RE = re.compile(r"SKU[- ]?(\d[\d-]*)", re.I)


def _normalize_tokens(text: str) -> set[str]:
    return {
        t
        for t in "".join(c if c.isalnum() else " " for c in text.lower()).split()
        if t
    }


def _sku_from_question(question: str) -> str | None:
    m = _SKU_RE.search(question)
    if not m:
        return None
    return f"SKU-{m.group(1).upper()}"


def mock_query(
    question: str,
    *,
    sku: str | None = None,
    vendor: str | None = None,
) -> dict[str, Any]:
    """Answer from fixture QA snippets + SKU history."""
    q_lower = question.lower()
    q_tokens = _normalize_tokens(question)
    best: dict[str, Any] | None = None
    best_score = 0
    for snip in load_historical_prices().get("qa_snippets", []):
        needles = [n.lower() for n in snip.get("question_contains", [])]
        score = sum(1 for n in needles if n in q_lower)
        score += sum(1 for n in needles if n.replace("-", "") in q_tokens or n in q_tokens)
        if score > best_score:
            best_score = score
            best = snip

    hist = get_sku_history(sku) if sku else None
    if hist is None:
        inferred = _sku_from_question(question)
        if inferred:
            hist = get_sku_history(inferred)

    if best and best_score > 0:
        facts = dict(best.get("facts") or {})
        unit = facts.get("unit_price")
        return {
            "answer": best["answer"],
            "facts": facts,
            "source": "mock",
            "historical_unit_price": float(unit)
            if unit is not None
            else (float(hist["avg_paid_unit_price"]) if hist else None),
            "contract_unit_price": (
                float(hist["contract_unit_price"])
                if hist and hist.get("contract_unit_price") is not None
                else None
            ),
            "empty": False,
        }

    if hist:
        price = hist.get("avg_paid_unit_price") or hist.get("last_paid_unit_price")
        contract = hist.get("contract_unit_price")
        vendor_name = hist.get("vendor") or vendor or "unknown"
        answer = (
            f"Historical paid unit price for {hist['sku']} from {vendor_name} "
            f"is ${float(price):.2f}"
            + (
                f" (contract ${float(contract):.2f})."
                if contract is not None
                else "."
            )
        )
        return {
            "answer": answer,
            "facts": {
                "sku": hist["sku"],
                "vendor": vendor_name,
                "unit_price": price,
                "contract_unit_price": contract,
                "invoice_ids": hist.get("invoice_ids", []),
            },
            "source": "mock",
            "historical_unit_price": float(price) if price is not None else None,
            "contract_unit_price": float(contract) if contract is not None else None,
            "empty": False,
        }

    if vendor:
        for row in load_historical_prices().get("vendor_spend", []):
            if str(row.get("vendor", "")).lower() == vendor.lower():
                return {
                    "answer": (
                        f"{row['vendor']} {row['period']} spend is "
                        f"${row['total_spend']:,.2f}."
                    ),
                    "facts": dict(row),
                    "source": "mock",
                    "historical_unit_price": None,
                    "contract_unit_price": None,
                    "empty": False,
                }

    return {
        "answer": "No matching FinOps mock facts for that question.",
        "facts": {},
        "source": "mock",
        "historical_unit_price": None,
        "contract_unit_price": None,
        "empty": True,
    }


def mock_review(invoice_id: str) -> dict[str, Any]:
    case = get_review_case(invoice_id)
    if not case:
        return {
            "found": False,
            "invoice_id": invoice_id.strip().upper(),
            "recommendation": "Reject",
            "rationale": "Invoice not found in mock FinOps review cases.",
            "source": "mock",
        }
    return {
        "found": True,
        "source": "mock",
        **{k: v for k, v in case.items()},
    }


def live_query(
    question: str,
    *,
    settings: Settings | None = None,
    use_llm: bool = False,
) -> dict[str, Any]:
    settings = settings or get_settings()
    base = settings.finops_api_url.rstrip("/")
    timeout = settings.finops_timeout_seconds
    retries = max(1, settings.finops_retries)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(
                    f"{base}/api/query",
                    json={"question": question, "use_llm": use_llm},
                )
                res.raise_for_status()
                payload = res.json()
            facts = payload.get("facts") or {}
            unit = None
            for key in ("unit_price", "avg_unit_price", "historical_unit_price"):
                if key in facts and facts[key] is not None:
                    unit = float(facts[key])
                    break
            contract = facts.get("contract_unit_price")
            return {
                "answer": payload.get("answer") or payload.get("explanation") or "",
                "facts": facts,
                "source": "live",
                "historical_unit_price": unit,
                "contract_unit_price": float(contract) if contract is not None else None,
                "empty": False,
                "raw": payload,
            }
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(0.15 * (attempt + 1))
    raise RuntimeError(f"FinOps live query failed after {retries} attempts: {last_exc}")


def live_review(
    invoice_id: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    base = settings.finops_api_url.rstrip("/")
    timeout = settings.finops_timeout_seconds
    retries = max(1, settings.finops_retries)
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(
                    f"{base}/api/review",
                    json={"invoice_id": invoice_id, "include_qty": False},
                )
                if res.status_code == 404:
                    return {
                        "found": False,
                        "invoice_id": invoice_id.strip().upper(),
                        "recommendation": "Reject",
                        "rationale": "Invoice not found in live FinOps ledger.",
                        "source": "live",
                    }
                res.raise_for_status()
                payload = res.json()
            alerts = payload.get("alerts") or []
            drift = next(
                (a for a in alerts if a.get("severity") == "price_drift"),
                None,
            )
            return {
                "found": bool(payload.get("found", True)),
                "source": "live",
                "invoice_id": str(payload.get("invoice_id", invoice_id)).upper(),
                "vendor": payload.get("vendor"),
                "po_number": payload.get("po_number"),
                "sku": (drift or {}).get("sku"),
                "invoice_unit_price": (drift or {}).get("invoice_unit_price")
                or (drift or {}).get("unit_price"),
                "contract_unit_price": (drift or {}).get("contract_unit_price"),
                "drift_pct": (drift or {}).get("drift_pct"),
                "max_price_drift_pct": (payload.get("contract") or {}).get(
                    "max_price_drift_pct"
                ),
                "po_match": payload.get("po_match"),
                "recommendation": payload.get("recommendation", "Reject"),
                "rationale": payload.get("summary")
                or "; ".join(payload.get("reasons") or []),
                "raw": payload,
            }
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(0.15 * (attempt + 1))
    raise RuntimeError(f"FinOps live review failed after {retries} attempts: {last_exc}")


def query_with_mode(
    question: str,
    *,
    sku: str | None = None,
    vendor: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    mode = settings.finops_mode.lower()
    if mode == "mock":
        return mock_query(question, sku=sku, vendor=vendor)
    if mode != "live":
        raise ValueError(f"Unsupported FINOPS_MODE: {settings.finops_mode}")
    try:
        return live_query(question, settings=settings)
    except Exception:
        fallback = mock_query(question, sku=sku, vendor=vendor)
        fallback["source"] = "mock_fallback"
        fallback["live_error"] = True
        return fallback


def review_with_mode(
    invoice_id: str,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    mode = settings.finops_mode.lower()
    if mode == "mock":
        return mock_review(invoice_id)
    if mode != "live":
        raise ValueError(f"Unsupported FINOPS_MODE: {settings.finops_mode}")
    try:
        return live_review(invoice_id, settings=settings)
    except Exception:
        fallback = mock_review(invoice_id)
        fallback["source"] = "mock_fallback"
        fallback["live_error"] = True
        return fallback
