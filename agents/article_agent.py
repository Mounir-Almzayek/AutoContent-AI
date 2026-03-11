"""
Article Generator Agent: produces full article text from the content brief.
See docs/02_AI_AGENTS_SPEC.md § 3.
"""
import logging
from typing import Any, Optional

from services.openrouter_service import OpenRouterService, OpenRouterError, get_openrouter_service

logger = logging.getLogger(__name__)


def _build_article_prompt(brief: dict) -> str:
    """Build the user prompt for article generation from brief."""
    title = brief.get("title") or "Article"
    h1 = brief.get("h1") or title
    h2_list = brief.get("h2") or []
    h3_map = brief.get("h3") or {}
    faq = brief.get("faq") or []
    target_kw = brief.get("target_keywords") or []
    tone = brief.get("tone") or "professional"
    word_target = brief.get("word_count_target") or 1500

    sections = []
    for h2 in h2_list:
        sections.append(f"## {h2}")
        for h3 in (h3_map.get(h2) or [])[:5]:
            sections.append(f"### {h3}")
        sections.append("[Write 2-4 paragraphs here]")

    structure = "\n".join(sections)
    faq_text = "\n".join(
        f"Q: {q.get('question', '')}\nA: {q.get('answer', '')}" for q in faq[:5]
    ) if faq else "None"
    keywords_str = ", ".join(target_kw) if target_kw else ""

    return (
        f"Write a full SEO article with this structure. Use Markdown.\n\n"
        f"Title: {title}\nH1: {h1}\n\n"
        f"Target length: about {word_target} words. Tone: {tone}.\n"
        f"Target keywords to use naturally: {keywords_str or 'N/A'}\n\n"
        f"Structure to follow:\n{structure}\n\n"
        f"Include an FAQ section at the end:\n{faq_text}\n\n"
        f"Output the complete article in Markdown (headings, paragraphs, list if needed). "
        f"Do not output JSON or meta—only the article body."
    )


def run_article_generator(
    state: dict[str, Any],
    *,
    openrouter: Optional[OpenRouterService] = None,
) -> dict[str, Any]:
    """
    Node function for LangGraph. Reads `brief` from state.
    Writes `content` (full article text) and `last_usage` into state.
    """
    brief = state.get("brief")
    if not brief or not isinstance(brief, dict):
        return {"error": "Missing brief", "current_node": "article_generator"}

    service = openrouter or get_openrouter_service()
    user_content = _build_article_prompt(brief)

    try:
        content, usage = service.chat(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert content writer. Write clear, engaging, SEO-friendly articles in the requested structure and tone. Output only the article in Markdown, no preamble.",
                },
                {"role": "user", "content": user_content},
            ],
        )
    except OpenRouterError as e:
        logger.exception("Article agent OpenRouter error: %s", e)
        return {"error": str(e), "current_node": "article_generator"}

    if not (content and content.strip()):
        return {"error": "Article agent returned empty content", "current_node": "article_generator"}

    return {
        "content": content.strip(),
        "last_usage": usage,
        "current_node": "article_generator",
    }
