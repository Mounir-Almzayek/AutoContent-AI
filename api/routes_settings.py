"""
AI settings: default model + per-agent model overrides. Each agent can use a different model.
See docs/05_API_DESIGN.md and docs/08_OPENROUTER_INTEGRATION.md.
"""
from fastapi import APIRouter

from app.config import get_settings
from api.schemas import AISettingsPerAgent
from services.agent_settings import AGENT_IDS, get_agent_overrides, set_agent_overrides

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/ai", response_model=AISettingsPerAgent)
def get_ai_settings():
    """Return default model + per-agent model overrides."""
    s = get_settings()
    default, agents = get_agent_overrides()
    if not default:
        default = {"model": s.default_model, "temperature": s.default_temperature, "max_tokens": s.default_max_tokens}
    # Ensure all agent IDs exist in response (dashboard can show all)
    out_agents = dict(agents)
    for aid in AGENT_IDS:
        if aid not in out_agents:
            out_agents[aid] = {"model": ""}
    return AISettingsPerAgent(default=default, agents=out_agents)


@router.patch("/ai", response_model=AISettingsPerAgent)
def update_ai_settings(body: AISettingsPerAgent):
    """Update default and per-agent model overrides. Stored in memory; used by all agents."""
    default = body.default or {}
    agents = {k: v for k, v in (body.agents or {}).items() if k in AGENT_IDS}
    set_agent_overrides(default, agents)
    return get_ai_settings()
