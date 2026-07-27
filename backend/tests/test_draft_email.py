"""draft_email tool tests."""

from app.llm.provider import MockLLMClient
from app.tools.contracts import DraftEmailInput, ToolStatus
from app.tools.draft_email import draft_email, parse_email_draft


def test_draft_email_happy_path_mock():
    result = draft_email(
        vendor="Alpha Supplies",
        sku="SKU-1001",
        quantity=500,
        quoted_unit_price=10.8,
        target_unit_price=9.95,
        intent="negotiate_price",
        context="Coastal Widgets offers $9.95; FinOps history $10.00.",
        llm=MockLLMClient(),
    )
    assert result.status == ToolStatus.OK
    assert result.data is not None
    assert result.data.vendor == "Alpha Supplies"
    assert "SKU-1001" in result.data.subject
    assert "Alpha Supplies" in result.data.body
    assert "HITL" in result.observation


def test_draft_email_input_model():
    result = draft_email(
        DraftEmailInput(
            vendor="Beta Parts",
            sku="SKU-1001",
            quantity=100,
            quoted_unit_price=11.5,
            target_unit_price=10.0,
        ),
        llm=MockLLMClient(),
    )
    assert result.status == ToolStatus.OK
    assert "Beta Parts" in result.data.body


def test_parse_email_fallback_when_empty():
    inp = DraftEmailInput(
        vendor="Nova Components",
        sku="SKU-1001",
        quantity=250,
        quoted_unit_price=10.25,
        target_unit_price=10.0,
    )
    subject, body = parse_email_draft("", inp)
    assert "SKU-1001" in subject
    assert "Nova Components" in body
    assert "$10.25" in body


def test_parse_email_body_only():
    inp = DraftEmailInput(
        vendor="X",
        sku="SKU-1",
        quantity=10,
        quoted_unit_price=1.0,
    )
    subject, body = parse_email_draft("Just a freeform note about pricing.", inp)
    assert subject  # fallback subject
    assert body == "Just a freeform note about pricing."


def test_draft_email_decline_intent_fallback_llm():
    class BlankLLM:
        def complete(self, system: str, user: str) -> str:
            return ""

    result = draft_email(
        vendor="Gamma Logistics",
        sku="SKU-1001-ALT",
        quantity=200,
        quoted_unit_price=9.5,
        intent="decline",
        llm=BlankLLM(),
    )
    assert result.status == ToolStatus.OK
    assert "will not proceed" in result.data.body.lower()
