"""
Articles CRUD, generate pipeline, and publish (stub).
See docs/05_API_DESIGN.md.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from api.schemas import GenerateRequest, GenerateResponse
from models.article import Article, ArticleCreate, ArticleResponse, ArticleUpdate
from graphs.content_generation_graph import run_content_generation
from services.token_tracker import TokenTracker

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("", response_model=dict)
def list_articles(
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List articles with optional status filter and pagination."""
    base = select(Article)
    if status:
        base = base.where(Article.status == status)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar() or 0
    q = base.order_by(Article.created_at.desc()).offset(skip).limit(limit)
    rows = db.execute(q).scalars().all()
    return {"items": [ArticleResponse.model_validate(r) for r in rows], "total": total}


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """Get a single article by ID."""
    row = db.get(Article, article_id)
    if not row:
        raise HTTPException(status_code=404, detail="Article not found")
    return ArticleResponse.model_validate(row)


@router.post("", response_model=ArticleResponse, status_code=201)
def create_article(body: ArticleCreate, db: Session = Depends(get_db)):
    """Create an article manually (no AI)."""
    article = Article(
        keyword_id=body.keyword_id,
        title=body.title,
        content=body.content,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        status=body.status,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return ArticleResponse.model_validate(article)


@router.post("/generate", response_model=GenerateResponse)
def generate_article(body: GenerateRequest, db: Session = Depends(get_db)):
    """Run the AI content generation pipeline for the given keyword."""
    opts = body.options
    keyword = body.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword is required")

    # Load existing articles for duplicate check (id, title, content snippet)
    existing_q = (
        select(Article.id, Article.title, Article.content)
        .where(Article.status.in_(["ready", "published"]))
        .order_by(Article.updated_at.desc())
        .limit(100)
    )
    existing_rows = db.execute(existing_q).all()
    existing_articles = [
        {
            "id": r.id,
            "title": r.title,
            "content_snippet": (r.content or "")[:500],
        }
        for r in existing_rows
    ]

    language = opts.language if opts else "en"
    word_count_target = opts.word_count_target if opts else 1500
    tone = opts.tone if opts else "professional"
    try:
        state = run_content_generation(
            keyword,
            language=language,
            word_count_target=word_count_target,
            tone=tone,
            keyword_id=None,
            existing_articles=existing_articles,
            db_session=db,
        )
    except Exception as e:
        return GenerateResponse(error=str(e), status="failed")

    # Log token usage from last agent that ran (if present)
    last_usage = state.get("last_usage")
    if last_usage and isinstance(last_usage, dict):
        from app.config import get_settings
        tracker = TokenTracker(db)
        tracker.log(
            model=get_settings().default_model,
            tokens_prompt=last_usage.get("prompt_tokens", 0),
            tokens_completion=last_usage.get("completion_tokens", 0),
            article_id=state.get("article_id"),
            cost=last_usage.get("total_cost"),
        )

    if state.get("error"):
        return GenerateResponse(error=state["error"], status="failed")
    if state.get("is_duplicate"):
        return GenerateResponse(error="Duplicate content rejected", status="duplicate_rejected")
    if state.get("article_id"):
        return GenerateResponse(article_id=state["article_id"], status="success")
    return GenerateResponse(error="No article produced", status="failed")


@router.patch("/{article_id}", response_model=ArticleResponse)
def update_article(article_id: int, body: ArticleUpdate, db: Session = Depends(get_db)):
    """Update an article (partial)."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(article, k, v)
    db.commit()
    db.refresh(article)
    return ArticleResponse.model_validate(article)


@router.delete("/{article_id}", status_code=204)
def delete_article(article_id: int, db: Session = Depends(get_db)):
    """Delete an article."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return None


@router.post("/{article_id}/publish")
def publish_article(article_id: int, db: Session = Depends(get_db)):
    """Publish article to WordPress. Implemented in Phase 4 (WordPress integration)."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    raise HTTPException(
        status_code=501,
        detail="WordPress publish will be implemented in Phase 4",
    )
