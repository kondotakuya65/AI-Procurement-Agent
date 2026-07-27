"""Email reflection (writer → reviewer) tests."""

from app.llm.provider import MockLLMClient
from app.tools.contracts import DraftEmailInput
from app.tools.draft_email import draft_email
from app.tools.email_reflection import reflect_on_draft, review_draft


class WeakThenRewriteLLM:
    """First writer call returns a weak draft; rewrite returns a full one."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        sys_l = system.lower()
        if "communications reviewer" in sys_l:
            return "VERDICT: REWRITE\nCRITIQUE: Missing pricing ask."
        if "revising a previous draft" in sys_l or "reviewer critique:" in user.lower():
            return (
                "Subject: Revised pricing request for SKU-1001\n\n"
                "Dear Alpha Supplies,\n\n"
                "We are procuring 500 units of SKU-1001. Your quote is $10.80/unit; "
                "please match our $9.95–$10.00 benchmark.\n\n"
                "Regards,\nProcurement"
            )
        # Initial weak writer output (no price, short)
        return "Subject: Hi\n\nThanks."


def test_heuristic_flags_short_body():
    inp = DraftEmailInput(
        vendor="Alpha Supplies",
        sku="SKU-1001",
        quantity=500,
        quoted_unit_price=10.8,
        target_unit_price=10.0,
    )
    review = review_draft(
        subject="Hi",
        body="Thanks.",
        inp=inp,
        llm=MockLLMClient(),
    )
    assert review["passed"] is False
    assert review["source"] == "heuristic"


def test_reflect_rewrites_weak_draft():
    inp = DraftEmailInput(
        vendor="Alpha Supplies",
        sku="SKU-1001",
        quantity=500,
        quoted_unit_price=10.8,
        target_unit_price=9.95,
    )
    llm = WeakThenRewriteLLM()
    subject, body, meta = reflect_on_draft(
        subject="Hi",
        body="Thanks.",
        inp=inp,
        llm=llm,
        enabled=True,
    )
    assert meta["rewritten"] is True
    assert "10.80" in body or "10.8" in body
    assert "Alpha Supplies" in body
    assert subject.startswith("Revised")


def test_draft_email_reflection_disabled_skips_rewrite(monkeypatch):
    monkeypatch.setenv("EMAIL_REFLECTION", "false")
    from app.config import clear_settings_cache

    clear_settings_cache()
    llm = WeakThenRewriteLLM()
    result = draft_email(
        vendor="Alpha Supplies",
        sku="SKU-1001",
        quantity=500,
        quoted_unit_price=10.8,
        target_unit_price=10.0,
        llm=llm,
        reflection=False,
    )
    assert result.data is not None
    assert result.data.reflection is not None
    assert result.data.reflection["enabled"] is False
    assert result.data.reflection["rewritten"] is False
    # Weak first draft kept when reflection off
    assert result.data.subject == "Hi"
    clear_settings_cache()


def test_draft_email_reflection_rewrites_when_enabled():
    llm = WeakThenRewriteLLM()
    result = draft_email(
        vendor="Alpha Supplies",
        sku="SKU-1001",
        quantity=500,
        quoted_unit_price=10.8,
        target_unit_price=10.0,
        llm=llm,
        reflection=True,
    )
    assert result.data is not None
    assert result.data.reflection["rewritten"] is True
    assert "SKU-1001" in result.data.body
    assert "Reviewer requested rewrite" in result.observation


def test_strong_mock_draft_passes_reflection():
    result = draft_email(
        vendor="Alpha Supplies",
        sku="SKU-1001",
        quantity=500,
        quoted_unit_price=10.8,
        target_unit_price=9.95,
        llm=MockLLMClient(),
        reflection=True,
    )
    assert result.data is not None
    assert result.data.reflection["enabled"] is True
    assert result.data.reflection["rewritten"] is False
    assert "Reviewer PASS" in result.observation
