"""
API request/response schemas (non-DB). See docs/05_API_DESIGN.md and docs/07_DATA_MODELS.md.
"""
from typing import Any, Optional

from pydantic import BaseModel, Field


class GenerateOptions(BaseModel):
    language: str = Field(default="en", description="Content language")
    tone: str = Field(default="professional", description="Tone: professional, friendly, technical, conversational")
    word_count_target: int = Field(default=1500, ge=100, le=20000)
    model_override: Optional[str] = Field(default=None, description="Override default LLM model (e.g. openai/gpt-4o)")


class GenerateRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=512)
    options: Optional[GenerateOptions] = None


class GenerateResponse(BaseModel):
    article_id: Optional[int] = None
    error: Optional[str] = None
    status: str = Field(..., description="success | failed | duplicate_rejected")


class ArticleListResponse(BaseModel):
    items: list[Any]  # ArticleResponse from models
    total: int


class KeywordListResponse(BaseModel):
    items: list[Any]  # KeywordResponse from models
    total: int


class AISettings(BaseModel):
    model: str = Field(..., description="LLM model identifier")
    temperature: float = Field(..., ge=0, le=2)
    max_tokens: int = Field(..., ge=1, le=128_000)


class ScheduleArticleRequest(BaseModel):
    article_id: int
    scheduled_at: str = Field(..., description="ISO 8601 datetime")


class ScheduleGenerationRequest(BaseModel):
    keyword_id: int
    scheduled_at: str = Field(..., description="ISO 8601 datetime")
