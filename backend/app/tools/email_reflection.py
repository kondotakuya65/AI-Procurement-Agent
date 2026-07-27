"""Writer → reviewer reflection loop for negotiation emails."""

from __future__ import annotations

import re
from typing import Any

from app.llm.provider import LLMClient
from app.tools.contracts import DraftEmailInput

REVIEWER_SYSTEM = """You are a senior procurement communications reviewer.
Evaluate the draft email for: professionalism, factual prices, clear ask, no threats.
Reply in this exact format:
VERDICT: PASS
or
VERDICT: REWRITE
CRITIQUE: <one or two sentences>
"""

REWRITE_SYSTEM = """You are a professional procurement specialist revising a vendor email.
Rules:
- Output exactly: a Subject line starting with "Subject:", then a blank line, then the body.
- Be concise, factual, and polite. No threats or legal language.
- Use only the numbers and facts provided. Do not invent prices.
- Address reviewer critique while keeping Subject:/body format.
"""


def _heuristic_weak(subject: str, body: str, inp: DraftEmailInput) -> str | None:
    """Deterministic weakness checks (used by mock + as safety net)."""
    text = f"{subject}\n{body}".lower()
    if len(body.strip()) < 40:
        return "Body is too short to be a professional vendor email."
    if inp.vendor.lower() not in body.lower() and "dear" not in body.lower():
        return "Draft should address the vendor by name."
    if str(inp.sku).lower() not in text:
        return "SKU is missing from the draft."
    if "threat" in text or "lawsuit" in text or "legal action" in text:
        return "Tone is too aggressive / legalistic."
    if inp.intent == "negotiate_price":
        quoted = f"{inp.quoted_unit_price:.2f}"
        if quoted not in text and f"{inp.quoted_unit_price:g}" not in text:
            return "Quoted unit price is missing from the draft."
    return None


def review_draft(
    *,
    subject: str,
    body: str,
    inp: DraftEmailInput,
    llm: LLMClient,
) -> dict[str, Any]:
    """Return {passed: bool, critique: str, source: heuristic|llm}."""
    weak = _heuristic_weak(subject, body, inp)
    if weak:
        return {"passed": False, "critique": weak, "source": "heuristic"}

    user = (
        f"Vendor: {inp.vendor}\nSKU: {inp.sku}\nIntent: {inp.intent}\n\n"
        f"Subject: {subject}\n\n{body}\n"
    )
    raw = llm.complete(REVIEWER_SYSTEM, user)
    verdict = "PASS"
    critique = "Looks professional and complete."
    m = re.search(r"VERDICT:\s*(PASS|REWRITE)", raw, re.I)
    if m:
        verdict = m.group(1).upper()
    c = re.search(r"CRITIQUE:\s*(.+)", raw, re.I | re.S)
    if c:
        critique = c.group(1).strip().splitlines()[0].strip()
    if verdict == "REWRITE":
        return {
            "passed": False,
            "critique": critique or "Needs revision.",
            "source": "llm",
        }
    return {"passed": True, "critique": critique, "source": "llm"}


def rewrite_draft(
    *,
    subject: str,
    body: str,
    critique: str,
    inp: DraftEmailInput,
    llm: LLMClient,
) -> tuple[str, str]:
    # Lazy import avoids circular dependency with draft_email
    from app.tools.draft_email import parse_email_draft

    target = (
        f"${inp.target_unit_price:.2f}"
        if inp.target_unit_price is not None
        else "(not specified)"
    )
    user = (
        "Please rewrite an improved vendor email.\n\n"
        f"Intent: {inp.intent}\n"
        f"Vendor: {inp.vendor}\n"
        f"SKU: {inp.sku}\n"
        f"Quantity: {inp.quantity}\n"
        f"Quoted unit price: ${inp.quoted_unit_price:.2f}\n"
        f"Target unit price: {target}\n"
        f"Extra context:\n{inp.context.strip() or '(none)'}\n\n"
        f"Previous draft:\nSubject: {subject}\n\n{body}\n\n"
        f"Reviewer critique: {critique}\n"
    )
    raw = llm.complete(REWRITE_SYSTEM, user)
    return parse_email_draft(raw, inp)


def reflect_on_draft(
    *,
    subject: str,
    body: str,
    inp: DraftEmailInput,
    llm: LLMClient,
    enabled: bool = True,
) -> tuple[str, str, dict[str, Any]]:
    """Optionally review+rewrite. Returns subject, body, reflection meta."""
    meta: dict[str, Any] = {
        "enabled": enabled,
        "passed": True,
        "rewritten": False,
        "critique": None,
        "source": None,
    }
    if not enabled:
        return subject, body, meta

    review = review_draft(subject=subject, body=body, inp=inp, llm=llm)
    meta["passed"] = bool(review["passed"])
    meta["critique"] = review.get("critique")
    meta["source"] = review.get("source")
    if review["passed"]:
        return subject, body, meta

    from app.agent.progress import emit_progress

    emit_progress(
        f"Rewriting weak draft: {review.get('critique')}",
        node="draft_email",
        phase="rewrite",
    )
    new_subject, new_body = rewrite_draft(
        subject=subject,
        body=body,
        critique=str(review.get("critique") or "Improve professionalism."),
        inp=inp,
        llm=llm,
    )
    meta["rewritten"] = True
    meta["passed"] = True
    return new_subject, new_body, meta
