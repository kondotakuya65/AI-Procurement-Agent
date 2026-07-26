"""LLM provider adapter (full ollama/openai/anthropic/mock in A3)."""

from __future__ import annotations

from typing import Protocol

from app.config import Settings, get_settings


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class MockLLMClient:
    def complete(self, system: str, user: str) -> str:
        return (
            "Mock LLM: procurement agent scaffold is online. "
            "Wire LangGraph tools in later commits."
        )


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    if settings.llm_provider.lower() == "mock":
        return MockLLMClient()
    # Full providers land in commit A3
    return MockLLMClient()
