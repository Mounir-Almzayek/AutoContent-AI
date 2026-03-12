"""
SEO Optimizer Agent: improves meta title, meta description, and optional FAQ schema from article + brief.
See docs/architecture/ai-agents.md.
"""
import json
import logging
import re
from typing import Any, Optional

from services.agent_settings import get_model_for_agent
from services.openrouter_service import OpenRouterService, OpenRouterError, get_openrouter_service

logger = logging.getLogger(__name__)

SEO_SYSTEM = """You are an SEO specialist. Given an article (Markdown) and its brief, output a JSON object only (no markdown, no code block):
{
  "optimized_content": "the same or slightly improved article body in Markdown (fix headings/emphasis if needed)",
  "meta_title": "SEO meta title, ~50-60 chars",
  "meta_description": "Meta description, ~150-155 chars",
  "internal_linking_suggestions": ["suggested anchor text and topic 1", "suggested anchor text and topic 2"],
  "faq_schema": [{"question": "...", "answer": "..."}]
}
- meta_title and meta_description must be compelling and keyword-aware.
- faq_schema: copy from the article's FAQ section if present, same format as brief FAQ."""


def run_seo_optimizer(
    state: dict[str, Any],
    *,
    openrouter: Optional[OpenRouterService] = None,
) -> dict[str, Any]:
    """
    Node function for LangGraph. Reads `content` and `brief` from state.
    Writes `content` (optimized), `seo_result` (meta_title, meta_description, faq_schema, internal_linking_suggestions), and `last_usage`.
    """
    content = (state.get("content") or "").strip()
    brief = state.get("brief") or {}

    if not content:
        return {"error": "Missing content for SEO optimizer", "current_node": "seo_optimizer"}

    service = openrouter or get_openrouter_service()
    title = brief.get("title") or brief.get("h1") or "Article"
    user_msg = (
        f"Article title from brief: {title}\n\nArticle body (first 4000 chars):\n{content[:4000]}\n\n"
        "Respond with JSON only. For optimized_content, return the full article if it's already good, or a slightly improved version."
    )

    try:
        raw, usage = service.chat(
            messages=[
                {"role": "system", "content": SEO_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=get_model_for_agent("seo_agent"),
        )
    except OpenRouterError as e:
        logger.exception("SEO agent OpenRouter error: %s", e)
        return {"error": str(e), "current_node": "seo_optimizer"}

    parsed = _parse_seo_response(raw, content)
    if parsed is None:
        # Fallback: keep content, use brief title as meta
        meta_desc = (content[:155].replace("\n", " ") if content else "") or title
        return {
            "content": content,
            "seo_result": {
                "meta_title": title[:60] if title else "Article",
                "meta_description": meta_desc[:155],
                "faq_schema": brief.get("faq") or [],
                "internal_linking_suggestions": [],
            },
            "last_usage": usage,
            "current_node": "seo_optimizer",
        }

    return {
        "content": parsed.get("optimized_content") or content,
        "seo_result": {
            "meta_title": parsed.get("meta_title") or title[:60],
            "meta_description": parsed.get("meta_description") or content[:155].replace("\n", " "),
            "faq_schema": parsed.get("faq_schema") or brief.get("faq") or [],
            "internal_linking_suggestions": parsed.get("internal_linking_suggestions") or [],
        },
        "last_usage": usage,
        "current_node": "seo_optimizer",
    }


def _parse_seo_response(content: str, fallback_content: str) -> Optional[dict[str, Any]]:
    """Extract SEO JSON from LLM response."""
    text = content.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            return None
        opt = data.get("optimized_content")
        if not opt or not isinstance(opt, str):
            opt = fallback_content
        meta_title = (data.get("meta_title") or "").strip()[:70]
        meta_desc = (data.get("meta_description") or "").strip()[:160]
        faq = data.get("faq_schema")
        if not isinstance(faq, list):
            faq = []
        faq = [{"question": str(x.get("question", "")), "answer": str(x.get("answer", ""))} for x in faq if isinstance(x, dict) and x.get("question")][:10]
        links = data.get("internal_linking_suggestions")
        if not isinstance(links, list):
            links = []
        links = [str(x).strip() for x in links if x][:5]
        return {
            "optimized_content": opt,
            "meta_title": meta_title or "Article",
            "meta_description": meta_desc or fallback_content[:155].replace("\n", " "),
            "faq_schema": faq,
            "internal_linking_suggestions": links,
        }
    except (json.JSONDecodeError, TypeError):
        return None
