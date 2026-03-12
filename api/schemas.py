"""
API request/response schemas (non-DB). See docs/api/design.md and docs/data/models.md.
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


class AISettingsPerAgent(BaseModel):
    """Default model + per-agent overrides. Each agent can have its own model on the dashboard."""
    default: dict = Field(default_factory=lambda: {"model": "", "temperature": 0.7, "max_tokens": 4096})
    agents: dict[str, dict] = Field(default_factory=dict, description="agent_id -> { model: str }")


class ScheduleArticleRequest(BaseModel):
    article_id: int
    scheduled_at: str = Field(..., description="ISO 8601 datetime")


class ScheduleGenerationRequest(BaseModel):
    keyword_id: int
    scheduled_at: str = Field(..., description="ISO 8601 datetime")


# --- Trend Discovery ---

class TrendDiscoveryRequest(BaseModel):
    niche: str = Field(..., min_length=1, max_length=256, description="Target industry or domain (e.g. AI tools, digital marketing)")
    language: str = Field(default="en", max_length=16)
    number_of_keywords: int = Field(default=5, ge=1, le=20, description="How many trend keywords to generate")
    time_window: str = Field(default="last month", max_length=64, description="e.g. last week, last month, current trends")


class TrendItem(BaseModel):
    trend_topic: str = ""
    primary_keyword: str
    long_tail_keywords: list[str] = Field(default_factory=list)
    search_intent: str = "Informational"
    article_title: str = ""
    article_description: str = ""
    suggested_sections: list[str] = Field(default_factory=list)
    recommended_word_count: int = 1500


class TrendDiscoveryResponse(BaseModel):
    items: list[TrendItem]
    usage: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class ImportFromTrendsRequest(BaseModel):
    """Payload to import trend items as keywords (by primary_keyword + optional topic/search_intent)."""
    items: list[TrendItem] = Field(..., min_length=1, max_length=100)
