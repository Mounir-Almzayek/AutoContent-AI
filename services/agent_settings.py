"""
Per-agent AI settings (model override). Used by all agents so the dashboard model choice is applied.
The settings API writes here; agents read via get_model_for_agent().
"""
from app.config import get_settings

# agent_id -> { "model": "..." }. Empty = use default.
_agent_overrides: dict[str, dict[str, str | int | float]] = {}

# Default (fallback when no agent override). Keys: model, temperature, max_tokens.
_default: dict[str, str | int | float] = {}

# All agent IDs that can have a dedicated model on the dashboard.
AGENT_IDS = [
    "keyword_agent",
    "brief_agent",
    "article_agent",
    "quality_agent",
    "duplicate_agent",
    "seo_agent",
    "trend_agent",
]


def get_model_for_agent(agent_id: str) -> str:
    """Return the model string to use for this agent (override or default or config)."""
    s = get_settings()
    if agent_id in _agent_overrides and _agent_overrides[agent_id].get("model"):
        return str(_agent_overrides[agent_id]["model"]).strip()
    if _default.get("model"):
        return str(_default["model"]).strip()
    return s.default_model or "openai/gpt-4o"


def get_temperature_for_agent(agent_id: str) -> float:
    """Return temperature for this agent."""
    s = get_settings()
    if agent_id in _agent_overrides and "temperature" in _agent_overrides[agent_id]:
        return float(_agent_overrides[agent_id]["temperature"])
    if "temperature" in _default:
        return float(_default["temperature"])
    return s.default_temperature


def get_max_tokens_for_agent(agent_id: str) -> int:
    """Return max_tokens for this agent."""
    s = get_settings()
    if agent_id in _agent_overrides and "max_tokens" in _agent_overrides[agent_id]:
        return int(_agent_overrides[agent_id]["max_tokens"])
    if "max_tokens" in _default:
        return int(_default["max_tokens"])
    return s.default_max_tokens


def set_agent_overrides(default: dict, agents: dict[str, dict]) -> None:
    """Set overrides from API. default = { model?, temperature?, max_tokens? }, agents = { agent_id: { model? } }."""
    global _default, _agent_overrides
    _default = dict(default) if default else {}
    _agent_overrides = {k: dict(v) for k, v in (agents or {}).items() if k in AGENT_IDS}


def get_agent_overrides() -> tuple[dict, dict]:
    """Return (default, agents) for API/dashboard."""
    return dict(_default), {k: dict(v) for k, v in _agent_overrides.items()}
