"""
AI settings (model, temperature, max_tokens). In-memory override for Phase 3.
See docs/05_API_DESIGN.md and docs/08_OPENROUTER_INTEGRATION.md.
"""
from fastapi import APIRouter

from app.config import get_settings
from api.schemas import AISettings

router = APIRouter(prefix="/settings", tags=["Settings"])

# In-memory overrides (Phase 3). Phase 6 could replace with DB or file.
_ai_overrides: dict = {}


@router.get("/ai", response_model=AISettings)
def get_ai_settings():
    """Return current AI settings (from env + optional overrides)."""
    s = get_settings()
    overrides = _ai_overrides
    return AISettings(
        model=overrides.get("model") or s.default_model,
        temperature=overrides.get("temperature") if "temperature" in overrides else s.default_temperature,
        max_tokens=overrides.get("max_tokens") if "max_tokens" in overrides else s.default_max_tokens,
    )


@router.patch("/ai", response_model=AISettings)
def update_ai_settings(body: AISettings):
    """Update AI settings (stored in memory for this process)."""
    global _ai_overrides
    _ai_overrides = {
        "model": body.model,
        "temperature": body.temperature,
        "max_tokens": body.max_tokens,
    }
    return get_ai_settings()
