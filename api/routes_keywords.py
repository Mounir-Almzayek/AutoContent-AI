"""
Keywords CRUD, import, and trend discovery. See docs/05_API_DESIGN.md.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from agents.trend_agent import run_trend_discovery
from api.schemas import (
    ImportFromTrendsRequest,
    TrendDiscoveryRequest,
    TrendDiscoveryResponse,
    TrendItem,
)
from models.keyword import Keyword, KeywordCreate, KeywordResponse, KeywordUpdate
from services.token_tracker import TokenTracker

router = APIRouter(prefix="/keywords", tags=["Keywords"])


@router.get("", response_model=dict)
def list_keywords(
    status: Optional[str] = Query(None, description="Filter by status"),
    q: Optional[str] = Query(None, description="Search by keyword name (case-insensitive)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List keywords with optional status filter, search by name, and pagination."""
    base = select(Keyword)
    if status:
        base = base.where(Keyword.status == status)
    if q and q.strip():
        base = base.where(Keyword.keyword.ilike(f"%{q.strip()}%"))
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar() or 0
    query = base.order_by(Keyword.created_at.desc()).offset(skip).limit(limit)
    rows = db.execute(query).scalars().all()
    return {"items": [KeywordResponse.model_validate(r) for r in rows], "total": total}


@router.get("/{keyword_id}", response_model=KeywordResponse)
def get_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """Get a single keyword by ID."""
    row = db.get(Keyword, keyword_id)
    if not row:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return KeywordResponse.model_validate(row)


@router.post("", response_model=KeywordResponse, status_code=201)
def create_keyword(body: KeywordCreate, db: Session = Depends(get_db)):
    """Add a single keyword."""
    existing = db.execute(select(Keyword).where(Keyword.keyword == body.keyword.strip())).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Keyword already exists")
    kw = Keyword(keyword=body.keyword.strip(), status="pending")
    db.add(kw)
    db.commit()
    db.refresh(kw)
    return KeywordResponse.model_validate(kw)


@router.patch("/{keyword_id}", response_model=KeywordResponse)
def update_keyword(keyword_id: int, body: KeywordUpdate, db: Session = Depends(get_db)):
    """Update a keyword (partial)."""
    kw = db.get(Keyword, keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(kw, k, v)
    db.commit()
    db.refresh(kw)
    return KeywordResponse.model_validate(kw)


@router.delete("/{keyword_id}", status_code=204)
def delete_keyword(keyword_id: int, db: Session = Depends(get_db)):
    """Delete a keyword."""
    kw = db.get(Keyword, keyword_id)
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found")
    db.delete(kw)
    db.commit()
    return None


@router.post("/import", response_model=dict)
def import_keywords(file: UploadFile, db: Session = Depends(get_db)):
    """Import keywords from a text or CSV file (one keyword per line or comma-separated)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file")
    content = file.file.read().decode("utf-8", errors="replace")
    seen = set()
    added = 0
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for part in line.replace(",", " ").split():
            kw = part.strip()
            if kw and kw.lower() not in seen:
                seen.add(kw.lower())
                existing = db.execute(select(Keyword).where(Keyword.keyword == kw)).scalars().first()
                if not existing:
                    db.add(Keyword(keyword=kw, status="pending"))
                    added += 1
    db.commit()
    return {"imported": added, "total_unique": len(seen)}


# ---------- Trend Discovery ----------


@router.post("/trend-discovery", response_model=TrendDiscoveryResponse)
def trend_discovery(
    body: TrendDiscoveryRequest,
    db: Session = Depends(get_db),
):
    """
    Discover trending topics and generate a batch of keywords + article ideas.
    Uses the Trend Content Discovery Agent (LLM). Token usage is logged.
    """
    items, usage = run_trend_discovery(
        niche=body.niche,
        language=body.language,
        number_of_keywords=body.number_of_keywords,
        time_window=body.time_window,
    )
    if usage and isinstance(usage, dict):
        tracker = TokenTracker(db)
        tracker.log(
            model=get_settings().default_model,
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            cost=usage.get("total_cost"),
        )
    # Normalize to TrendItem for response
    out_items = [
        TrendItem(
            trend_topic=i.get("trend_topic", ""),
            primary_keyword=i.get("primary_keyword", ""),
            long_tail_keywords=i.get("long_tail_keywords") or [],
            search_intent=i.get("search_intent", "Informational"),
            article_title=i.get("article_title", ""),
            article_description=i.get("article_description", ""),
            suggested_sections=i.get("suggested_sections") or [],
            recommended_word_count=i.get("recommended_word_count", 1500),
        )
        for i in items
    ]
    return TrendDiscoveryResponse(items=out_items, usage=usage)


@router.post("/import-from-trends", response_model=dict)
def import_from_trends(body: ImportFromTrendsRequest, db: Session = Depends(get_db)):
    """
    Create keywords from trend discovery results (one keyword per item's primary_keyword).
    Sets topic and search_intent from the trend item for the content pipeline.
    """
    imported = 0
    for item in body.items:
        kw = (item.primary_keyword or "").strip()
        if not kw:
            continue
        existing = db.execute(select(Keyword).where(Keyword.keyword == kw)).scalars().first()
        if existing:
            continue
        topic = (item.article_title or item.trend_topic or "").strip() or None
        intent = (item.search_intent or "").strip() or None
        db.add(
            Keyword(
                keyword=kw,
                topic=topic[:512] if topic else None,
                search_intent=intent[:64] if intent else None,
                status="pending",
            )
        )
        imported += 1
    db.commit()
    return {"imported": imported, "total_requested": len(body.items)}
