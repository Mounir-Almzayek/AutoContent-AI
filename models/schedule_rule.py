"""
Recurring schedule rule for automated article generation.
See docs/12_CONTENT_CALENDAR_DESIGN.md.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base as SQLBase


class ScheduleRule(SQLBase):
    __tablename__ = "schedule_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False)  # interval | cron
    interval_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    articles_per_run: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    keyword_filter: Mapped[str] = mapped_column(String(32), default="all_pending", nullable=False)  # all_pending | ids
    keyword_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array or comma-separated
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    tone: Mapped[str] = mapped_column(String(32), default="professional", nullable=False)
    word_count_target: Mapped[int] = mapped_column(Integer, default=1500, nullable=False)
    publish_behavior: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)  # draft | immediate | delay
    publish_delay_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_articles_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScheduleRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    trigger_type: str = Field(..., pattern="^(interval|cron)$")
    interval_minutes: Optional[int] = Field(None, ge=1, le=525600)
    cron_expression: Optional[str] = Field(None, max_length=128)
    articles_per_run: int = Field(1, ge=1, le=20)
    keyword_filter: str = Field("all_pending", pattern="^(all_pending|ids)$")
    keyword_ids: Optional[str] = None
    language: str = Field("en", max_length=16)
    tone: str = Field("professional", max_length=32)
    word_count_target: int = Field(1500, ge=300, le=20000)
    publish_behavior: str = Field("draft", pattern="^(draft|immediate|delay)$")
    publish_delay_minutes: Optional[int] = Field(None, ge=0, le=10080)
    enabled: bool = True


class ScheduleRuleCreate(ScheduleRuleBase):
    pass


class ScheduleRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    trigger_type: Optional[str] = Field(None, pattern="^(interval|cron)$")
    interval_minutes: Optional[int] = Field(None, ge=1, le=525600)
    cron_expression: Optional[str] = Field(None, max_length=128)
    articles_per_run: Optional[int] = Field(None, ge=1, le=20)
    keyword_filter: Optional[str] = Field(None, pattern="^(all_pending|ids)$")
    keyword_ids: Optional[str] = None
    language: Optional[str] = Field(None, max_length=16)
    tone: Optional[str] = Field(None, max_length=32)
    word_count_target: Optional[int] = Field(None, ge=300, le=20000)
    publish_behavior: Optional[str] = Field(None, pattern="^(draft|immediate|delay)$")
    publish_delay_minutes: Optional[int] = Field(None, ge=0, le=10080)
    enabled: Optional[bool] = None


class ScheduleRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    trigger_type: str
    interval_minutes: Optional[int] = None
    cron_expression: Optional[str] = None
    articles_per_run: int
    keyword_filter: str
    keyword_ids: Optional[str] = None
    language: str
    tone: str
    word_count_target: int
    publish_behavior: str
    publish_delay_minutes: Optional[int] = None
    enabled: bool
    last_run_at: Optional[datetime] = None
    last_articles_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
