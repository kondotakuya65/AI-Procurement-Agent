from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    cors_origins: str = "http://localhost:3001"
    app_port: int = 8100

    database_url: str = "sqlite:///./dev.db"

    llm_provider: str = "mock"  # ollama | openai | anthropic | mock
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi3:mini"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"
    llm_timeout_seconds: float = 45.0

    finops_mode: str = "mock"  # live | mock
    finops_api_url: str = "http://localhost:8000"
    finops_timeout_seconds: float = 15.0
    finops_retries: int = 2

    fixtures_dir: str = str(_repo_root() / "fixtures")
    outbox_dir: str = "./outbox"

    # Stretch: writer → reviewer loop on draft_email
    email_reflection: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
