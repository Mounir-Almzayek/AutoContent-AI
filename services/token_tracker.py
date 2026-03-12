"""
Token usage logging and aggregation for LLM calls.
See docs/integration/openrouter.md and docs/data/models.md.
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.token_usage import TokenUsage, TokenUsageSummary


class TokenTracker:
    """Log and query token usage by period or by article."""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        model: str,
        tokens_prompt: int,
        tokens_completion: int,
        article_id: Optional[int] = None,
        cost: Optional[float] = None,
    ) -> TokenUsage:
        """Record one LLM call."""
        total = tokens_prompt + tokens_completion
        row = TokenUsage(
            model=model,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            total_tokens=total,
            cost=cost,
            article_id=article_id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_usage_by_period(
        self,
        period: str = "day",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> TokenUsageSummary:
        """
        Aggregate usage for a period. If start/end are given, they override period.

        period: "day" | "week" | "month" — relative to now.
        """
        now = datetime.utcnow()
        if end is None:
            end = now
        if start is None:
            if period == "day":
                start = now - timedelta(days=1)
            elif period == "week":
                start = now - timedelta(weeks=1)
            elif period == "month":
                start = now - timedelta(days=30)
            else:
                start = now - timedelta(days=1)

        q = (
            select(
                func.coalesce(func.sum(TokenUsage.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(TokenUsage.tokens_prompt), 0).label("prompt_tokens"),
                func.coalesce(func.sum(TokenUsage.tokens_completion), 0).label("completion_tokens"),
                func.sum(TokenUsage.cost).label("total_cost"),
                func.count(TokenUsage.id).label("record_count"),
            )
            .where(TokenUsage.created_at >= start, TokenUsage.created_at <= end)
        )
        row = self.db.execute(q).one()
        return TokenUsageSummary(
            period_start=start,
            period_end=end,
            total_tokens=row.total_tokens or 0,
            total_prompt_tokens=row.prompt_tokens or 0,
            total_completion_tokens=row.completion_tokens or 0,
            total_cost=float(row.total_cost) if row.total_cost is not None else None,
            record_count=row.record_count or 0,
        )

    def get_usage_by_article(self, article_id: int) -> TokenUsageSummary:
        """Aggregate usage for a single article."""
        q = (
            select(
                func.coalesce(func.sum(TokenUsage.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(TokenUsage.tokens_prompt), 0).label("prompt_tokens"),
                func.coalesce(func.sum(TokenUsage.tokens_completion), 0).label("completion_tokens"),
                func.sum(TokenUsage.cost).label("total_cost"),
                func.count(TokenUsage.id).label("record_count"),
            )
            .where(TokenUsage.article_id == article_id)
        )
        row = self.db.execute(q).one()
        return TokenUsageSummary(
            total_tokens=row.total_tokens or 0,
            total_prompt_tokens=row.prompt_tokens or 0,
            total_completion_tokens=row.completion_tokens or 0,
            total_cost=float(row.total_cost) if row.total_cost is not None else None,
            record_count=row.record_count or 0,
        )

    def get_total_cost(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Optional[float]:
        """Return total cost for the given time range (or all time if both None)."""
        q = select(func.sum(TokenUsage.cost)).where(TokenUsage.cost.isnot(None))
        if start is not None:
            q = q.where(TokenUsage.created_at >= start)
        if end is not None:
            q = q.where(TokenUsage.created_at <= end)
        row = self.db.execute(q).scalar()
        return float(row) if row is not None else None


def create_tracker(db: Session) -> TokenTracker:
    """Create a TokenTracker for the given session (e.g. from get_db)."""
    return TokenTracker(db)
