from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    if settings.llm_provider == "ollama":
        model = settings.ollama_model
    elif settings.llm_provider == "openai":
        model = settings.openai_model
    elif settings.llm_provider == "anthropic":
        model = settings.anthropic_model
    else:
        model = "mock"
    return {
        "status": "ok",
        "service": "ai-procurement-agent",
        "environment": settings.environment,
        "llm_provider": settings.llm_provider,
        "llm_model": model,
        "finops_mode": settings.finops_mode,
        "finops_api_url": settings.finops_api_url,
        "database_url_scheme": settings.database_url.split(":", 1)[0],
    }
