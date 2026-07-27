"""draft_email — LLM-backed professional negotiation draft (+ optional reflection)."""

from __future__ import annotations

import re
import time

from app.config import get_settings
from app.llm.provider import LLMClient, get_llm_client
from app.tools.contracts import (
    DraftEmailData,
    DraftEmailInput,
    ToolName,
    ToolResult,
)
from app.tools.email_reflection import reflect_on_draft

SYSTEM_PROMPT = """You are a professional procurement specialist writing vendor emails.
Rules:
- Output exactly: a Subject line starting with "Subject:", then a blank line, then the body.
- Be concise, factual, and polite. No threats or legal language.
- Use only the numbers and facts provided. Do not invent prices.
- Do not claim the email was sent; this is a draft for human approval.
"""


def _build_user_prompt(inp: DraftEmailInput) -> str:
    target = (
        f"${inp.target_unit_price:.2f}"
        if inp.target_unit_price is not None
        else "(not specified)"
    )
    return (
        "Please draft an email with the following details.\n\n"
        f"Intent: {inp.intent}\n"
        f"Vendor: {inp.vendor}\n"
        f"SKU: {inp.sku}\n"
        f"Quantity: {inp.quantity}\n"
        f"Quoted unit price: ${inp.quoted_unit_price:.2f}\n"
        f"Target unit price: {target}\n"
        f"Extra context:\n{inp.context.strip() or '(none)'}\n"
    )


def _fallback_draft(inp: DraftEmailInput) -> tuple[str, str]:
    target_line = ""
    if inp.target_unit_price is not None:
        target_line = (
            f" We are targeting approximately ${inp.target_unit_price:.2f}/unit "
            "based on historical/competitive pricing."
        )
    if inp.intent == "decline":
        subject = f"Decision on {inp.sku} quote"
        body = (
            f"Dear {inp.vendor},\n\n"
            f"Thank you for the quote of ${inp.quoted_unit_price:.2f}/unit "
            f"for {inp.quantity} units of {inp.sku}. After review, we will not "
            "proceed with this offer at this time.\n\n"
            "Regards,\nProcurement"
        )
    elif inp.intent == "request_quote":
        subject = f"RFQ: {inp.quantity} units of {inp.sku}"
        body = (
            f"Dear {inp.vendor},\n\n"
            f"Please provide a firm quote for {inp.quantity} units of {inp.sku}."
            f"{target_line}\n\n"
            "Regards,\nProcurement"
        )
    else:
        subject = f"Request for revised pricing on {inp.sku}"
        body = (
            f"Dear {inp.vendor},\n\n"
            f"We are procuring {inp.quantity} units of {inp.sku}. "
            f"Your current quote is ${inp.quoted_unit_price:.2f}/unit."
            f"{target_line} "
            "Please confirm whether you can revise pricing accordingly.\n\n"
            "Regards,\nProcurement"
        )
    if inp.context.strip():
        body = body.replace(
            "\n\nRegards,",
            f"\n\nAdditional context: {inp.context.strip()}\n\nRegards,",
        )
    return subject, body


def parse_email_draft(text: str, inp: DraftEmailInput) -> tuple[str, str]:
    """Extract subject/body; fall back to a deterministic template if needed."""
    cleaned = text.strip()
    if not cleaned:
        return _fallback_draft(inp)

    subject_match = re.search(
        r"(?im)^\s*subject\s*:\s*(.+)$",
        cleaned,
    )
    if subject_match:
        subject = subject_match.group(1).strip()
        after = cleaned[subject_match.end() :].lstrip("\r\n")
        body = after.strip()
        if body:
            return subject, body

    # No subject line — treat whole text as body
    subject, body = _fallback_draft(inp)
    return subject, cleaned


def draft_email(
    inp: DraftEmailInput | None = None,
    *,
    vendor: str | None = None,
    sku: str | None = None,
    quantity: int | None = None,
    quoted_unit_price: float | None = None,
    target_unit_price: float | None = None,
    intent: str = "negotiate_price",
    context: str = "",
    llm: LLMClient | None = None,
    reflection: bool | None = None,
) -> ToolResult[DraftEmailData]:
    started = time.perf_counter()
    try:
        if inp is None:
            if vendor is None or sku is None or quantity is None or quoted_unit_price is None:
                raise ValueError(
                    "vendor, sku, quantity, and quoted_unit_price are required"
                )
            inp = DraftEmailInput(
                vendor=vendor,
                sku=sku,
                quantity=quantity,
                quoted_unit_price=quoted_unit_price,
                target_unit_price=target_unit_price,
                intent=intent,
                context=context,
            )

        client = llm or get_llm_client()
        settings = get_settings()
        use_reflection = (
            settings.email_reflection if reflection is None else reflection
        )

        from app.agent.progress import emit_progress

        emit_progress(
            f"LLM drafting email to {inp.vendor}…",
            node="draft_email",
            phase="writer",
        )
        raw = client.complete(SYSTEM_PROMPT, _build_user_prompt(inp))
        subject, body = parse_email_draft(raw, inp)
        if use_reflection:
            emit_progress(
                "Reviewer checking draft quality…",
                node="draft_email",
                phase="reviewer",
            )
        subject, body, reflection_meta = reflect_on_draft(
            subject=subject,
            body=body,
            inp=inp,
            llm=client,
            enabled=use_reflection,
        )
        if reflection_meta.get("rewritten"):
            emit_progress(
                "Reviewer requested rewrite — revised draft ready.",
                node="draft_email",
                phase="rewritten",
            )
        data = DraftEmailData(
            vendor=inp.vendor,
            subject=subject,
            body=body,
            intent=inp.intent,
            reflection=reflection_meta,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        reflect_note = ""
        if reflection_meta.get("enabled"):
            if reflection_meta.get("rewritten"):
                reflect_note = " Reviewer requested rewrite; revised draft ready."
            else:
                reflect_note = " Reviewer PASS."
        return ToolResult.ok(
            ToolName.DRAFT_EMAIL,
            data,
            observation=(
                f"Drafted email to {data.vendor}: “{data.subject}” "
                f"({len(data.body)} chars).{reflect_note} Awaiting HITL approval."
            ),
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - started) * 1000
        return ToolResult.fail(
            ToolName.DRAFT_EMAIL,
            str(exc),
            latency_ms=latency_ms,
        )
