"""Persist approved email drafts to the local outbox (no SMTP)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings


def outbox_root() -> Path:
    settings = get_settings()
    path = Path(settings.outbox_dir)
    if not path.is_absolute():
        # Resolve relative to backend cwd by default
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_outbox_email(
    *,
    draft: dict[str, Any],
    goal: str,
    thread_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write an approved draft as JSON under OUTBOX_DIR. Returns the file path."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    vendor = (draft.get("vendor") or "vendor").replace(" ", "_")
    name = f"{stamp}_{vendor}_approved.json"
    path = outbox_root() / name
    payload = {
        "approved_at": stamp,
        "goal": goal,
        "thread_id": thread_id,
        "draft": draft,
        "extra": extra or {},
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path
