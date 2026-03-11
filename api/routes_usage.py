"""
Token usage and aggregation. See docs/05_API_DESIGN.md.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from models.token_usage import TokenUsageSummary
from services.token_tracker import TokenTracker

router = APIRouter(prefix="/usage", tags=["Usage"])


@router.get("/tokens", response_model=TokenUsageSummary)
def get_usage_tokens(
    period: str = Query("day", description="day | week | month"),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    """Get token usage aggregated by period or custom start/end."""
    tracker = TokenTracker(db)
    return tracker.get_usage_by_period(period=period, start=start, end=end)


@router.get("/by-article", response_model=TokenUsageSummary)
def get_usage_by_article(
    article_id: int = Query(..., description="Article ID"),
    db: Session = Depends(get_db),
):
    """Get token usage for a single article."""
    tracker = TokenTracker(db)
    return tracker.get_usage_by_article(article_id)
