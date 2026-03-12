"""
Article Generator Agent: produces full article text from the content brief.
Uses web search for recent, real-world context when available.
See docs/02_AI_AGENTS_SPEC.md § 3.
"""
import logging
from typing import Any, Optional

from services.agent_settings import get_model_for_agent
from services.openrouter_service import OpenRouterService, OpenRouterError, get_openrouter_service
from services.web_search import search_web_for_topic

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
    Node function for LangGraph. Reads `brief` and `keyword` from state.
    Runs web search for the topic to ground the article in recent content, then writes the article.
    Writes `content` (full article text) and `last_usage` into state.
    """
    brief = state.get("brief")
    if not brief or not isinstance(brief, dict):
        return {"error": "Missing brief", "current_node": "article_generator"}

    keyword = (state.get("keyword") or "").strip()
    if not keyword and brief.get("target_keywords"):
        kw_list = brief.get("target_keywords") or []
        keyword = (kw_list[0] or "").strip() if kw_list else ""
    if not keyword:
        keyword = brief.get("title") or brief.get("h1") or ""

    web_context = search_web_for_topic(keyword, max_snippets=18, timelimit="m")
    user_content = _build_article_prompt(brief)
    if web_context:
        user_content = web_context + user_content

    system_msg = (
        "You are an expert content writer. Write clear, engaging, SEO-friendly articles "
        "in the requested structure and tone. Use the RECENT web/search results provided above "
        "to inform facts and context when present; prefer current, real-world information. "
        "Output only the article in Markdown, no preamble."
    )

    service = openrouter or get_openrouter_service()
    try:
        content, usage = service.chat(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content},
            ],
            model=get_model_for_agent("article_agent"),
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
