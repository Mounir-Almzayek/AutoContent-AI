"""
Article model: DB table and Pydantic schemas.
See docs/07_DATA_MODELS.md § 2.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base as SQLBase


# --- SQLAlchemy model ---

class Article(SQLBase):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    keyword_id: Mapped[Optional[int]] = mapped_column(ForeignKey("keywords.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta_title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    seo_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wordpress_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    keyword_rel = relationship("Keyword", back_populates="articles", foreign_keys=[keyword_id])


# --- Pydantic schemas ---

class ArticleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(...)
    meta_title: Optional[str] = Field(None, max_length=512)
    meta_description: Optional[str] = Field(None, max_length=512)
    status: str = Field(default="draft", pattern="^(draft|generating|ready|published|failed)$")


class ArticleCreate(ArticleBase):
    keyword_id: Optional[int] = None


class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=512)
    content: Optional[str] = None
    meta_title: Optional[str] = Field(None, max_length=512)
    meta_description: Optional[str] = Field(None, max_length=512)
    status: Optional[str] = Field(None, pattern="^(draft|generating|ready|published|failed)$")


class ArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    keyword_id: Optional[int] = None
    title: str
    content: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status: str
    seo_score: Optional[float] = None
    quality_score: Optional[float] = None
    wordpress_id: Optional[int] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
