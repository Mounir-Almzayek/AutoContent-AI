"""
Web search for agents: fetch recent snippets by topic/keyword (DuckDuckGo).
Used by trend discovery and article generation to ground content in real, up-to-date web results.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
    _HAS_WEB_SEARCH = True
except ImportError:
    try:
        from duckduckgo_search import DDGS  # legacy package name
        _HAS_WEB_SEARCH = True
    except ImportError:
        DDGS = None  # type: ignore
        _HAS_WEB_SEARCH = False


def search_web_for_topic(
    keyword: str,
    max_snippets: int = 20,
    timelimit: str = "m",
) -> str:
    """
    Search the web and news for a topic/keyword. Returns a string of snippets
    to inject into LLM prompts so content is based on recent, real-world information.

    Args:
        keyword: Topic or keyword to search for (e.g. article topic).
        max_snippets: Maximum number of snippets to return.
        timelimit: d=day, w=week, m=month, y=year.

    Returns:
        Formatted string of search results, or empty string if search fails/unavailable.
    """
    if not _HAS_WEB_SEARCH or not keyword or not keyword.strip():
        return ""

    current_year = datetime.now(timezone.utc).year
    k = keyword.strip()
    snippets: list[str] = []

    try:
        ddgs = DDGS()
        queries = [
            f"{k} {current_year}",
            f"latest {k}",
            f"{k} recent",
        ]
        for q in queries:
            for r in ddgs.text(q, max_results=5, timelimit=timelimit):
                if isinstance(r, dict):
                    title = (r.get("title") or "").strip()
                    body = (r.get("body") or "").strip()
                    if title or body:
                        snippets.append(f"- {title}\n  {body[:400]}")
            if len(snippets) >= max_snippets:
                break

        if len(snippets) < max_snippets:
            for r in ddgs.news(k, max_results=6, timelimit=timelimit):
                if isinstance(r, dict):
                    title = (r.get("title") or "").strip()
                    body = (r.get("body") or "").strip()
                    date = (r.get("date") or "").strip()
                    if title or body:
                        snippets.append(f"- [News] {title} {date}\n  {body[:350]}")
    except Exception as e:
        logger.warning("Web search for topic failed: %s", e)
        return ""

    if not snippets:
        return ""
    return (
        "Use the following RECENT web and news results to inform your article. "
        "Base facts and context on these real sources; prefer current information.\n\n"
        + "\n\n".join(snippets[:max_snippets])
        + "\n\n"
    )


def search_web_for_trends(niche: str, time_window: str, max_snippets: int = 25) -> str:
    """
    Web + news search for trend discovery (niche + time window).
    Returns formatted snippets string for the trend agent prompt.
    """
    if not _HAS_WEB_SEARCH or not niche or not niche.strip():
        return ""

    timelimit = "m"
    if "week" in time_window.lower():
        timelimit = "w"
    elif "day" in time_window.lower() or "current" in time_window.lower():
        timelimit = "d"

    current_year = datetime.now(timezone.utc).year
    k = niche.strip()
    snippets: list[str] = []

    try:
        ddgs = DDGS()
        for q in [
            f"trending {k} {current_year}",
            f"latest {k} news {current_year}",
            f"{k} popular topics",
        ]:
            for r in ddgs.text(q, max_results=5, timelimit=timelimit):
                if isinstance(r, dict):
                    title = (r.get("title") or "").strip()
                    body = (r.get("body") or "").strip()
                    if title or body:
                        snippets.append(f"- {title}\n  {body[:400]}")
            if len(snippets) >= max_snippets:
                break
        if len(snippets) < max_snippets:
            for r in ddgs.news(k, max_results=8, timelimit=timelimit):
                if isinstance(r, dict):
                    title = (r.get("title") or "").strip()
                    body = (r.get("body") or "").strip()
                    date = (r.get("date") or "").strip()
                    if title or body:
                        snippets.append(f"- [News] {title} {date}\n  {body[:350]}")
    except Exception as e:
        logger.warning("Web search for trends failed: %s", e)
        return ""

    if not snippets:
        return ""
    return (
        "Use the following REAL web and news results to base your trends on (prioritize these over generic knowledge). "
        "Use ONLY the current year given below in any dates or year references.\n\n"
        + "\n\n".join(snippets[:max_snippets])
        + "\n\nBased on the above, produce trend items that reflect these actual contemporary topics. "
        "All titles, long-tail keywords, and descriptions must use the CURRENT YEAR only—never 2023, 2024, or other past years.\n\n"
    )
