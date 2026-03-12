"""
Quality Checker Agent: evaluates readability, structure, keyword density, SEO and quality scores.
See docs/architecture/ai-agents.md.
"""
import json
import logging
import re
from typing import Any, Optional

from services.agent_settings import get_model_for_agent
from services.openrouter_service import OpenRouterService, OpenRouterError, get_openrouter_service

logger = logging.getLogger(__name__)

QUALITY_SYSTEM = """You are an SEO and content quality auditor. Given an article and its brief/target keywords, respond with a JSON object only (no markdown, no code block):
{
  "readability_score": 0-100,
  "keyword_density": 0.0-0.1 (e.g. 0.02 for 2%),
  "structure_ok": true/false,
  "content_completeness": 0-100,
  "seo_score": 0-100,
  "quality_score": 0-100,
  "suggestions": ["suggestion 1", "suggestion 2"]
}
- structure_ok: true if the article has clear H1/H2 (and H3 where expected) matching the brief.
- content_completeness: how well the article covers the intended outline (0-100).
- suggestions: 0-3 short improvement suggestions."""


def run_quality_check(
    state: dict[str, Any],
    *,
    openrouter: Optional[OpenRouterService] = None,
) -> dict[str, Any]:
    """
    Node function for LangGraph. Reads `content` and `brief` from state.
    Writes `quality_result` and `last_usage` into state.
    """
    content = (state.get("content") or "").strip()
    brief = state.get("brief") or {}

    if not content:
        return {"error": "Missing content for quality check", "current_node": "quality_check"}

    service = openrouter or get_openrouter_service()
    target_kw = brief.get("target_keywords") or []
    outline = f"Title: {brief.get('title')}; H2s: {brief.get('h2', [])}"

    user_msg = (
        f"Article (excerpt, first ~2000 chars):\n{content[:2000]}\n\n"
        f"Target keywords: {target_kw}\nOutline: {outline}\n\n"
        "Respond with JSON only."
    )

    try:
        raw, usage = service.chat(
            messages=[
                {"role": "system", "content": QUALITY_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=get_model_for_agent("quality_agent"),
        )
    except OpenRouterError as e:
        logger.exception("Quality agent OpenRouter error: %s", e)
        return {"error": str(e), "current_node": "quality_check"}

    result = _parse_quality_response(raw)
    if result is None:
        return {"error": "Quality agent returned invalid JSON", "current_node": "quality_check"}

    return {
        "quality_result": result,
        "last_usage": usage,
        "current_node": "quality_check",
    }


def _parse_quality_response(content: str) -> Optional[dict[str, Any]]:
    """Extract and clamp quality JSON from LLM response."""
    text = content.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            return None
        def clamp(n, lo, hi):
            try:
                x = float(n)
                return max(lo, min(hi, x))
            except (TypeError, ValueError):
                return lo
        suggestions = data.get("suggestions")
        if not isinstance(suggestions, list):
            suggestions = []
        suggestions = [str(s).strip() for s in suggestions if s][:5]
        return {
            "readability_score": clamp(data.get("readability_score"), 0, 100),
            "keyword_density": clamp(data.get("keyword_density"), 0, 0.2),
            "structure_ok": bool(data.get("structure_ok", True)),
            "content_completeness": clamp(data.get("content_completeness"), 0, 100),
            "seo_score": clamp(data.get("seo_score"), 0, 100),
            "quality_score": clamp(data.get("quality_score"), 0, 100),
            "suggestions": suggestions,
        }
    except (json.JSONDecodeError, TypeError):
        return None
