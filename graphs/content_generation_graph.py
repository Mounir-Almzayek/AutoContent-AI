"""
Content generation LangGraph workflow: Keyword → Brief → Article → Quality → Duplicate → SEO → Save.
See docs/architecture/langgraph-workflow.md.
"""
from typing import Any, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph

from agents.keyword_agent import run_keyword_analyzer
from agents.brief_agent import run_brief_agent
from agents.article_agent import run_article_generator
from agents.quality_agent import run_quality_check
from agents.duplicate_agent import run_duplicate_check
from agents.seo_agent import run_seo_optimizer


# --- State schema (all optional for incremental updates) ---

class ContentGenerationState(TypedDict, total=False):
    keyword: str
    language: str
    word_count_target: int
    tone: str
    keyword_analysis: dict[str, Any]
    brief: dict[str, Any]
    content: str
    quality_result: dict[str, Any]
    is_duplicate: bool
    duplicate_similarity: float
    most_similar_article_id: Optional[int]
    seo_result: dict[str, Any]
    article_id: Optional[int]
    error: str
    current_node: str
    last_usage: dict[str, Any]
    existing_articles: list[dict[str, Any]]
    keyword_id: Optional[int]
    _db: Any  # Session injected by caller for save_article; not serialized in output


# --- Node wrappers (signature: state -> state_update for LangGraph) ---

def _keyword_node(state: ContentGenerationState) -> dict[str, Any]:
    return run_keyword_analyzer(state)


def _brief_node(state: ContentGenerationState) -> dict[str, Any]:
    return run_brief_agent(state)


def _article_node(state: ContentGenerationState) -> dict[str, Any]:
    return run_article_generator(state)


def _quality_node(state: ContentGenerationState) -> dict[str, Any]:
    return run_quality_check(state)


def _duplicate_node(state: ContentGenerationState) -> dict[str, Any]:
    return run_duplicate_check(state)


def _seo_node(state: ContentGenerationState) -> dict[str, Any]:
    return run_seo_optimizer(state)


def _reject_node(state: ContentGenerationState) -> dict[str, Any]:
    """Mark as rejected (duplicate); go to END."""
    return {"current_node": "reject", "error": "Article rejected: duplicate content"}


def _save_article_node(state: ContentGenerationState) -> dict[str, Any]:
    """Persist article to DB when _db is in state (injected by API)."""
    from models.article import Article

    db = state.get("_db")
    if db is None:
        return {"error": "No DB session for save_article", "current_node": "save_article"}

    content = (state.get("content") or "").strip()
    brief = state.get("brief") or {}
    seo = state.get("seo_result") or {}
    quality = state.get("quality_result") or {}

    title = (brief.get("title") or brief.get("h1") or "Article").strip() or "Article"
    meta_title = (seo.get("meta_title") or title)[:512]
    meta_description = (seo.get("meta_description") or "")[:512] or None
    seo_score = quality.get("seo_score")
    quality_score = quality.get("quality_score")
    keyword_id = state.get("keyword_id")

    article = Article(
        keyword_id=keyword_id,
        title=title,
        content=content,
        meta_title=meta_title or None,
        meta_description=meta_description,
        status="ready",
        seo_score=float(seo_score) if seo_score is not None else None,
        quality_score=float(quality_score) if quality_score is not None else None,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return {"article_id": article.id, "current_node": "save_article"}


def _route_after_duplicate(state: ContentGenerationState) -> Literal["reject", "seo_optimizer"]:
    """Conditional edge: duplicate -> reject, else -> seo_optimizer."""
    if state.get("is_duplicate"):
        return "reject"
    return "seo_optimizer"


# --- Build and compile graph ---

def build_content_graph():
    """Build the content generation StateGraph and return compiled graph."""
    builder = StateGraph(ContentGenerationState)

    builder.add_node("keyword_analyzer", _keyword_node)
    builder.add_node("content_brief", _brief_node)
    builder.add_node("article_generator", _article_node)
    builder.add_node("quality_check", _quality_node)
    builder.add_node("duplicate_check", _duplicate_node)
    builder.add_node("seo_optimizer", _seo_node)
    builder.add_node("reject", _reject_node)
    builder.add_node("save_article", _save_article_node)

    builder.set_entry_point("keyword_analyzer")
    builder.add_conditional_edges(
        "keyword_analyzer",
        lambda s: "__end__" if s.get("error") else "content_brief",
        path_map={"__end__": END, "content_brief": "content_brief"},
    )
    builder.add_conditional_edges(
        "content_brief",
        lambda s: "__end__" if s.get("error") else "article_generator",
        path_map={"__end__": END, "article_generator": "article_generator"},
    )
    builder.add_conditional_edges(
        "article_generator",
        lambda s: "__end__" if s.get("error") else "quality_check",
        path_map={"__end__": END, "quality_check": "quality_check"},
    )
    builder.add_conditional_edges(
        "quality_check",
        lambda s: "__end__" if s.get("error") else "duplicate_check",
        path_map={"__end__": END, "duplicate_check": "duplicate_check"},
    )
    builder.add_conditional_edges(
        "duplicate_check",
        _route_after_duplicate,
        path_map={"reject": "reject", "seo_optimizer": "seo_optimizer"},
    )
    builder.add_conditional_edges(
        "seo_optimizer",
        lambda s: "__end__" if s.get("error") else "save_article",
        path_map={"__end__": END, "save_article": "save_article"},
    )
    builder.add_edge("save_article", END)
    builder.add_edge("reject", END)

    return builder.compile()


# Singleton compiled graph (optional; can rebuild per request if needed)
_compiled_graph = None


def get_content_graph():
    """Return the compiled content generation graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_content_graph()
    return _compiled_graph


def run_content_generation(
    keyword: str,
    *,
    language: str = "en",
    word_count_target: int = 1500,
    tone: str = "professional",
    keyword_id: Optional[int] = None,
    existing_articles: Optional[list[dict[str, Any]]] = None,
    db_session: Any = None,
) -> ContentGenerationState:
    """
    Run the full content generation pipeline.

    Caller should pass db_session (SQLAlchemy Session) so that save_article can persist the article.
    existing_articles: optional list of {"id", "title", "content_snippet"} for duplicate check.
    """
    initial: ContentGenerationState = {
        "keyword": keyword.strip(),
        "language": language,
        "word_count_target": word_count_target,
        "tone": tone,
        "keyword_id": keyword_id,
        "existing_articles": existing_articles or [],
    }
    if db_session is not None:
        initial["_db"] = db_session

    graph = get_content_graph()
    final = graph.invoke(initial)
    return final
