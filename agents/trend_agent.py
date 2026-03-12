"""
Trend Content Discovery Agent: discovers trending topics via web search, extracts keywords,
and produces article ideas ready for the content generation pipeline.
See docs/architecture/ai-agents.md and docs/api/design.md (trend-discovery).
"""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from services.agent_settings import get_model_for_agent
from services.openrouter_service import OpenRouterService, OpenRouterError, get_openrouter_service
from services.web_search import search_web_for_trends

logger = logging.getLogger(__name__)


TREND_SYSTEM = """You are a senior AI agent specialized in SEO research, trend analysis, and content discovery.

Your role is Trend Content Discovery. You must:

1. **Trend Discovery**: Identify RECENT and TRENDING topics using the WEB SEARCH RESULTS provided by the user when present. Prefer topics that appear in those results (news, articles, discussions). If no web results are given, use your knowledge but still focus on:
   - News and current industry discussions
   - Emerging technologies or updates
   - Popular tools or platforms
   - Recent product launches
   - Frequently searched topics in the given niche

2. **Keyword Extraction**: For each trend produce:
   - One **primary_keyword** (main target)
   - **long_tail_keywords**: 3–5 long-tail variations
   - **search_intent**: one of "Informational" | "Commercial" | "Transactional"

3. **Keyword Scoring**: Prefer high search interest, trend momentum, relevance, and SEO opportunity. Avoid duplicates or overly generic keywords.

4. **Content Planning**: For each keyword provide:
   - **article_title**: SEO-friendly, clickable
   - **article_description**: short 1–2 sentence description
   - **suggested_sections**: array of H2-style section titles (e.g. ["Introduction", "What is X", "Benefits", "How to get started", "Conclusion"])
   - **recommended_word_count**: integer (e.g. 1200–2000)

Respond with a single JSON object only (no markdown, no code block). Use this exact structure:

{
  "items": [
    {
      "trend_topic": "short trend label",
      "primary_keyword": "main keyword",
      "long_tail_keywords": ["kw1", "kw2", "kw3"],
      "search_intent": "Informational",
      "article_title": "SEO-Friendly Article Title",
      "article_description": "One or two sentences describing the article.",
      "suggested_sections": ["H2 One", "H2 Two", "H2 Three"],
      "recommended_word_count": 1500
    }
  ]
}

Rules:
- Return exactly the requested number of items (number_of_keywords).
- Focus on RECENT trends and emerging topics for the given time_window.
- All text in the requested language.
- suggested_sections: 3–6 section titles. recommended_word_count: 300–2500.
- CRITICAL: You will be given today's date and current year. Use ONLY the current year (e.g. 2025 or 2026) in article titles, long_tail_keywords, and article_description. NEVER use 2023, 2024, or any past year—this would make the content look outdated."""


def run_trend_discovery(
    niche: str,
    language: str = "en",
    number_of_keywords: int = 5,
    time_window: str = "last month",
    *,
    openrouter: Optional[OpenRouterService] = None,
) -> tuple[list[dict[str, Any]], Optional[dict[str, Any]]]:
    """
    Run trend discovery. Returns (list of trend items, usage dict or None on error).

    Each item has: trend_topic, primary_keyword, long_tail_keywords, search_intent,
    article_title, article_description, suggested_sections, recommended_word_count.
    """
    if not niche or not niche.strip():
        return [], None

    number_of_keywords = max(1, min(20, number_of_keywords))
    service = openrouter or get_openrouter_service()

    # Fetch real web/news snippets so the LLM bases trends on contemporary content
    web_context = search_web_for_trends(niche, time_window)
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    current_year = now.year

    user_msg = (
        f"Today's date: {today_str}. Current year: {current_year}. "
        f"All article titles, long_tail_keywords, and descriptions MUST reference {current_year} (or 'latest', 'current', 'recent') only. "
        "Do NOT use 2023, 2024, or any other past year—content must feel up-to-date.\n\n"
        + (web_context if web_context else "")
        + f"Niche/industry: {niche.strip()}\n"
        f"Language: {language}\n"
        f"Number of keywords/trends to generate: {number_of_keywords}\n"
        f"Time window for trends: {time_window}\n"
        "Respond with JSON only (object with 'items' array)."
    )

    try:
        content, usage = service.chat(
            messages=[
                {"role": "system", "content": TREND_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=get_model_for_agent("trend_agent"),
            max_tokens=8192,
        )
    except OpenRouterError as e:
        logger.exception("Trend agent OpenRouter error: %s", e)
        return [], None

    items = _parse_trend_response(content, number_of_keywords)
    return items, usage


def _parse_trend_response(content: str, expected_count: int) -> list[dict[str, Any]]:
    """Extract and normalize items from LLM JSON response."""
    text = content.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            return []
        raw_items = data.get("items")
        if not isinstance(raw_items, list):
            return []
        out = []
        for i, raw in enumerate(raw_items[: expected_count * 2]):
            if len(out) >= expected_count:
                break
            if not isinstance(raw, dict):
                continue
            item = _normalize_trend_item(raw)
            if item:
                out.append(item)
        return out
    except (json.JSONDecodeError, TypeError):
        return []


def _normalize_trend_item(raw: dict) -> Optional[dict[str, Any]]:
    """Build a single trend item with required fields."""
    primary = (raw.get("primary_keyword") or "").strip()
    if not primary:
        return None
    trend_topic = (raw.get("trend_topic") or primary)[:512]
    long_tail = raw.get("long_tail_keywords")
    if not isinstance(long_tail, list):
        long_tail = []
    long_tail = [str(k).strip() for k in long_tail if k][:5]
    intent = (raw.get("search_intent") or "Informational").strip()[:64]
    if intent not in ("Informational", "Commercial", "Transactional"):
        intent = "Informational"
    title = (raw.get("article_title") or primary)[:512]
    desc = (raw.get("article_description") or "")[:1024]
    sections = raw.get("suggested_sections")
    if not isinstance(sections, list):
        sections = []
    sections = [str(s).strip() for s in sections if s][:8]
    word_count = raw.get("recommended_word_count")
    if not isinstance(word_count, (int, float)) or word_count < 300:
        word_count = 1500
    word_count = min(2500, max(300, int(word_count)))

    return {
        "trend_topic": trend_topic,
        "primary_keyword": primary,
        "long_tail_keywords": long_tail,
        "search_intent": intent,
        "article_title": title,
        "article_description": desc,
        "suggested_sections": sections,
        "recommended_word_count": word_count,
    }
