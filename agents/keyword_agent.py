"""
Keyword Agent: analyzes a keyword and returns topic, search intent, and related keywords.
See docs/architecture/ai-agents.md.
"""
import json
import logging
import re
from typing import Any, Optional

from services.agent_settings import get_model_for_agent
from services.openrouter_service import OpenRouterService, OpenRouterError, get_openrouter_service

logger = logging.getLogger(__name__)

KEYWORD_SYSTEM = """You are an SEO expert. Analyze the given keyword and respond with a JSON object only (no markdown, no code block).
Use this exact structure:
{"topic": "main topic for an article", "search_intent": "informational"|"transactional"|"navigational", "related_keywords": ["keyword1", "keyword2", "keyword3"]}
- topic: one short phrase, the main subject for a single article.
- search_intent: one of informational, transactional, navigational.
- related_keywords: 3-5 related or long-tail keywords as a JSON array of strings."""


def run_keyword_analyzer(
    state: dict[str, Any],
    *,
    openrouter: Optional[OpenRouterService] = None,
) -> dict[str, Any]:
    """
    Node function for LangGraph. Reads `keyword` and optional `language` from state.
    Writes `keyword_analysis` and `last_usage` (for token tracking) into state.
    """
    keyword = (state.get("keyword") or "").strip()
    if not keyword:
        return {"error": "Missing keyword", "current_node": "keyword_analyzer"}

    service = openrouter or get_openrouter_service()
    language = state.get("language") or "en"
    user_msg = f"Keyword: {keyword}\nLanguage/audience: {language}\nRespond with JSON only."

    try:
        content, usage = service.chat(
            messages=[
                {"role": "system", "content": KEYWORD_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=get_model_for_agent("keyword_agent"),
        )
    except OpenRouterError as e:
        logger.exception("Keyword agent OpenRouter error: %s", e)
        return {"error": str(e), "current_node": "keyword_analyzer"}

    analysis = _parse_keyword_response(content)
    if analysis is None:
        return {"error": "Keyword agent returned invalid JSON", "current_node": "keyword_analyzer"}

    return {
        "keyword_analysis": analysis,
        "last_usage": usage,
        "current_node": "keyword_analyzer",
    }


def _parse_keyword_response(content: str) -> Optional[dict[str, Any]]:
    """Extract JSON from LLM response (strip markdown code block if present)."""
    text = content.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            return None
        topic = data.get("topic")
        intent = data.get("search_intent")
        related = data.get("related_keywords")
        if not isinstance(related, list):
            related = []
        related = [str(k) for k in related if k][:5]
        return {
            "topic": str(topic).strip() if topic else "",
            "search_intent": str(intent).strip().lower() if intent else "informational",
            "related_keywords": related,
        }
    except (json.JSONDecodeError, TypeError):
        return None
