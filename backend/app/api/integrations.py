"""Integration status: FinOps compose + vendor search mode."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.tools.live_search import probe_finops

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("")
def integrations_status() -> dict:
    settings = get_settings()
    finops = probe_finops(settings)
    return {
        "vendor_search_mode": settings.vendor_search_mode,
        "vendor_live_url_configured": bool((settings.vendor_live_url or "").strip()),
        "email_reflection": settings.email_reflection,
        "finops": finops,
        "compose_ready": (
            settings.finops_mode.lower() == "live" and bool(finops.get("reachable"))
        )
        or settings.finops_mode.lower() == "mock",
        "ports": {
            "agent_api": settings.app_port,
            "agent_ui": 3001,
            "finops_api": 8000,
            "finops_ui": 3000,
        },
        "hint": (
            "Run AI-FinOps-RAG on :8000 and set FINOPS_MODE=live to compose. "
            "Set VENDOR_SEARCH_MODE=hybrid to merge fixture + simulated live offers."
        ),
    }
