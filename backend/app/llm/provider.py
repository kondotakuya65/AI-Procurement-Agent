"""LLM provider adapter: ollama | openai | anthropic | mock."""

from __future__ import annotations

from typing import Protocol

import httpx

from app.config import Settings, get_settings


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class MockLLMClient:
    """Deterministic replies for tests / offline demos."""

    def complete(self, system: str, user: str) -> str:
        lower = user.lower()
        if "draft" in lower and ("email" in lower or "intent:" in lower):
            vendor = "Vendor"
            sku = "SKU-1001"
            qty = "500"
            quoted = "10.80"
            target = "10.00"
            for line in user.splitlines():
                if line.lower().startswith("vendor:"):
                    vendor = line.split(":", 1)[1].strip() or vendor
                elif line.lower().startswith("sku:"):
                    sku = line.split(":", 1)[1].strip() or sku
                elif line.lower().startswith("quantity:"):
                    qty = line.split(":", 1)[1].strip() or qty
                elif line.lower().startswith("quoted unit price:"):
                    quoted = line.split(":", 1)[1].strip().lstrip("$") or quoted
                elif line.lower().startswith("target unit price:"):
                    raw = line.split(":", 1)[1].strip()
                    if raw and "not specified" not in raw.lower():
                        target = raw.lstrip("$")
            return (
                f"Subject: Request for revised pricing on {sku}\n\n"
                f"Dear {vendor},\n\n"
                f"We are procuring {qty} units of {sku}. Your current quote is "
                f"${quoted}/unit. Our historical/contract benchmark is about "
                f"${target}/unit; please confirm if you can revise accordingly.\n\n"
                "Regards,\nProcurement"
            )
        if "plan" in lower or "next tool" in lower or "thought" in lower:
            return (
                "Thought: Compare vendor offers to FinOps historical price, then "
                "draft a negotiation email for HITL approval."
            )
        return (
            "Mock LLM: procurement agent online. "
            "Use tools for prices; human approves before send."
        )


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 45.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"num_predict": 512},
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return data.get("message", {}).get("content", "")


class OpenAIClient:
    def __init__(self, api_key: str, model: str, timeout: float = 45.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": 600,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]


class AnthropicClient:
    def __init__(self, api_key: str, model: str, timeout: float = 45.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 600,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        blocks = data.get("content") or []
        texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        return "\n".join(texts).strip()


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()
    timeout = settings.llm_timeout_seconds
    if provider == "mock":
        return MockLLMClient()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAIClient(settings.openai_api_key, settings.openai_model, timeout=timeout)
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        return AnthropicClient(
            settings.anthropic_api_key,
            settings.anthropic_model,
            timeout=timeout,
        )
    if provider == "ollama":
        return OllamaClient(settings.ollama_base_url, settings.ollama_model, timeout=timeout)
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
