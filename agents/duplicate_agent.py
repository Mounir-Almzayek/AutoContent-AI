"""
Duplication Checker Agent: compares new article with existing ones (by title/snippet) via LLM.
See docs/02_AI_AGENTS_SPEC.md § 5.
"""
import json
import logging
import re
from typing import Any, Optional

from services.openrouter_service import OpenRouterService, OpenRouterError, get_openrouter_service

logger = logging.getLogger(__name__)

DUPLICATE_SYSTEM = """You are a duplicate content detector. Given a new article (title + excerpt) and a list of existing articles (id, title), determine if the new article is a duplicate or near-duplicate of any existing one.
Respond with JSON only (no markdown, no code block):
{"is_duplicate": true|false, "similarity_score": 0.0-1.0, "most_similar_id": null|number}
- similarity_score: 0 = completely different, 1 = duplicate. If is_duplicate is true, score should be >= 0.8.
- most_similar_id: the id of the most similar existing article, or null if none."""


def run_duplicate_check(
    state: dict[str, Any],
    *,
    openrouter: Optional[OpenRouterService] = None,
) -> dict[str, Any]:
    """
    Node function for LangGraph. Reads `content`, optional `brief`, and optional `existing_articles` from state.
    existing_articles: list of {"id": int, "title": str, "content_snippet": str (optional)}.
    Writes `is_duplicate`, `duplicate_similarity`, `most_similar_article_id`, and optionally `last_usage`.
    """
    content = (state.get("content") or "").strip()
    existing = state.get("existing_articles") or []

    if not content:
        return {"error": "Missing content for duplicate check", "current_node": "duplicate_check"}

    # No existing articles → not duplicate
    if not existing or not isinstance(existing, list):
        return {
            "is_duplicate": False,
            "duplicate_similarity": 0.0,
            "most_similar_article_id": None,
            "current_node": "duplicate_check",
        }

    service = openrouter or get_openrouter_service()
    title = ""
    if isinstance(state.get("brief"), dict):
        title = (state["brief"].get("title") or state["brief"].get("h1") or "").strip()
    excerpt = content[:1500] if len(content) > 1500 else content

    existing_list = []
    for item in existing[:20]:
        if isinstance(item, dict) and item.get("id") is not None:
            existing_list.append({
                "id": int(item["id"]),
                "title": str(item.get("title") or "").strip(),
                "content_snippet": str(item.get("content_snippet") or item.get("content", ""))[:500],
            })

    if not existing_list:
        return {
            "is_duplicate": False,
            "duplicate_similarity": 0.0,
            "most_similar_article_id": None,
            "current_node": "duplicate_check",
        }

    user_msg = (
        f"New article title: {title}\nNew article excerpt:\n{excerpt}\n\n"
        f"Existing articles:\n{json.dumps(existing_list)}\n\n"
        "Respond with JSON only."
    )

    try:
        raw, usage = service.chat(
            messages=[
                {"role": "system", "content": DUPLICATE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
        )
    except OpenRouterError as e:
        logger.exception("Duplicate agent OpenRouter error: %s", e)
        return {"error": str(e), "current_node": "duplicate_check"}

    parsed = _parse_duplicate_response(raw)
    if parsed is None:
        # Default: not duplicate on parse failure to avoid blocking pipeline
        return {
            "is_duplicate": False,
            "duplicate_similarity": 0.0,
            "most_similar_article_id": None,
            "last_usage": usage,
            "current_node": "duplicate_check",
        }

    return {
        "is_duplicate": bool(parsed.get("is_duplicate", False)),
        "duplicate_similarity": float(parsed.get("similarity_score", 0)),
        "most_similar_article_id": parsed.get("most_similar_id"),
        "last_usage": usage,
        "current_node": "duplicate_check",
    }


def _parse_duplicate_response(content: str) -> Optional[dict[str, Any]]:
    """Extract is_duplicate, similarity_score, most_similar_id from LLM response."""
    text = content.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            return None
        score = data.get("similarity_score")
        try:
            score = max(0.0, min(1.0, float(score)))
        except (TypeError, ValueError):
            score = 0.0
        mid = data.get("most_similar_id")
        if mid is not None:
            try:
                mid = int(mid)
            except (TypeError, ValueError):
                mid = None
        return {
            "is_duplicate": bool(data.get("is_duplicate", False)),
            "similarity_score": score,
            "most_similar_id": mid,
        }
    except (json.JSONDecodeError, TypeError):
        return None
