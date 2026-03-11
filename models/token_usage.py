"""
Token usage model: DB table and Pydantic schemas for LLM usage tracking.
See docs/07_DATA_MODELS.md § 4 and docs/08_OPENROUTER_INTEGRATION.md.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base as SQLBase


# --- SQLAlchemy model ---

class TokenUsage(SQLBase):
    __tablename__ = "token_usage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tokens_prompt: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_completion: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    article_id: Mapped[Optional[int]] = mapped_column(ForeignKey("articles.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Pydantic schemas ---

class TokenUsageRecord(BaseModel):
    """Single usage record (for API responses)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str
    tokens_prompt: int
    tokens_completion: int
    total_tokens: int
    cost: Optional[float] = None
    article_id: Optional[int] = None
    created_at: datetime


class TokenUsageSummary(BaseModel):
    """Aggregated usage for a period or by article."""

    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost: Optional[float] = None
    record_count: int = 0
