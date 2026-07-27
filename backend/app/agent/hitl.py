"""HITL interrupt helpers."""

from __future__ import annotations

from typing import Any

from langgraph.types import Command

from app.tools.contracts import HitlDecision, HitlResumeInput


def parse_hitl_resume(value: Any) -> HitlResumeInput:
    if isinstance(value, HitlResumeInput):
        return value
    if isinstance(value, str):
        return HitlResumeInput(decision=HitlDecision(value.lower()))
    if isinstance(value, dict):
        return HitlResumeInput.model_validate(value)
    raise ValueError(f"Unsupported HITL resume payload: {type(value)!r}")


def resume_command(decision: str, edited_draft: str | None = None) -> Command:
    """Build a LangGraph Command to resume after hitl_gate interrupt."""
    payload: dict[str, Any] = {"decision": decision}
    if edited_draft is not None:
        payload["edited_draft"] = edited_draft
    # Validate early so API/tests fail clearly
    HitlResumeInput.model_validate(payload)
    return Command(resume=payload)


def apply_edited_draft(draft: dict[str, Any] | None, edited_text: str) -> dict[str, Any]:
    """Merge human edits into the email draft dict."""
    base = dict(draft or {})
    text = edited_text.strip()
    if text.lower().startswith("subject:"):
        lines = text.splitlines()
        subject = lines[0].split(":", 1)[1].strip()
        body = "\n".join(lines[1:]).lstrip()
        base["subject"] = subject
        base["body"] = body
    else:
        base["body"] = text
    return base
