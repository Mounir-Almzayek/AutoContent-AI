"""
Content Brief Agent: builds article outline (title, H1, H2, H3, FAQ, tone) from keyword analysis.
See docs/02_AI_AGENTS_SPEC.md § 2.
"""
import json
import logging
import re
from typing import Any, Optional

from services.agent_settings import get_model_for_agent
from services.openrouter_service import OpenRouterService, OpenRouterError, get_openrouter_service

logger = logging.getLogger(__name__)

BRIEF_SYSTEM = """You are an SEO content strategist. Given keyword analysis, produce a content brief as JSON only (no markdown, no code block).
Use this exact structure:
{
  "title": "Article title (SEO-friendly)",
  "h1": "Main H1 heading",
  "h2": ["H2 section 1", "H2 section 2", ...],
  "h3": {"H2 section 1": ["H3 a", "H3 b"], "H2 section 2": []},
  "faq": [{"question": "...", "answer": "..."}],
  "target_keywords": ["keyword1", "keyword2"],
  "tone": "professional"|"friendly"|"technical"|"conversational",
  "word_count_target": 1500
}
- h2: array of 3-6 H2 headings.
- h3: object mapping each H2 string to an array of H3 subheadings (can be empty).
- faq: 3-5 FAQ items with question and answer.
- word_count_target: integer, default 1500."""


def run_brief_agent(
    state: dict[str, Any],
    *,
    openrouter: Optional[OpenRouterService] = None,
) -> dict[str, Any]:
    """
    Node function for LangGraph. Reads `keyword_analysis` and optional `word_count_target`, `tone`, `language` from state.
    Writes `brief` and `last_usage` into state.
    """
    analysis = state.get("keyword_analysis")
    if not analysis or not isinstance(analysis, dict):
        return {"error": "Missing keyword_analysis", "current_node": "content_brief"}

    service = openrouter or get_openrouter_service()
    word_target = state.get("word_count_target") or 1500
    tone = state.get("tone") or "professional"
    language = state.get("language") or "en"

    user_msg = (
        f"Keyword analysis: {json.dumps(analysis)}\n"
        f"Target word count: {word_target}\nTone: {tone}\nLanguage: {language}\n"
        "Respond with JSON only."
    )

    try:
        content, usage = service.chat(
            messages=[
                {"role": "system", "content": BRIEF_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=get_model_for_agent("brief_agent"),
        )
    except OpenRouterError as e:
        logger.exception("Brief agent OpenRouter error: %s", e)
        return {"error": str(e), "current_node": "content_brief"}

    brief = _parse_brief_response(content)
    if brief is None:
        return {"error": "Brief agent returned invalid JSON", "current_node": "content_brief"}

    return {
        "brief": brief,
        "last_usage": usage,
        "current_node": "content_brief",
    }


def _parse_brief_response(content: str) -> Optional[dict[str, Any]]:
    """Extract and normalize brief JSON from LLM response."""
    text = content.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            return None
        h2 = data.get("h2")
        if not isinstance(h2, list):
            h2 = []
        h2 = [str(h).strip() for h in h2 if h][:8]
        h3 = data.get("h3")
        if not isinstance(h3, dict):
            h3 = {}
        h3_clean = {}
        for k, v in (h3 or {}).items():
            if isinstance(v, list):
                h3_clean[str(k).strip()] = [str(x).strip() for x in v if x][:5]
        faq = data.get("faq")
        if not isinstance(faq, list):
            faq = []
        faq_clean = []
        for item in faq[:6]:
            if isinstance(item, dict) and item.get("question"):
                faq_clean.append({
                    "question": str(item["question"]).strip(),
                    "answer": str(item.get("answer") or "").strip(),
                })
        return {
            "title": str(data.get("title") or "").strip() or "Article",
            "h1": str(data.get("h1") or "").strip() or data.get("title") or "Article",
            "h2": h2,
            "h3": h3_clean,
            "faq": faq_clean,
            "target_keywords": [str(k) for k in (data.get("target_keywords") or []) if k][:5],
            "tone": str(data.get("tone") or "professional").strip().lower(),
            "word_count_target": int(data.get("word_count_target") or 1500),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
