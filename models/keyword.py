"""
Keyword model: DB table and Pydantic schemas.
See docs/07_DATA_MODELS.md § 3.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base as SQLBase


# --- SQLAlchemy model ---

class Keyword(SQLBase):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    topic: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    search_intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    articles = relationship("Article", back_populates="keyword_rel", foreign_keys="Article.keyword_id")


# --- Pydantic schemas ---

class KeywordBase(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=512)


class KeywordCreate(KeywordBase):
    pass


class KeywordUpdate(BaseModel):
    keyword: Optional[str] = Field(None, min_length=1, max_length=512)
    topic: Optional[str] = None
    search_intent: Optional[str] = None
    status: Optional[str] = None


class KeywordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    keyword: str
    topic: Optional[str] = None
    search_intent: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
