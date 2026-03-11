"""
Application configuration loaded from environment variables.
See docs/08_OPENROUTER_INTEGRATION.md and docs/09_WORDPRESS_INTEGRATION.md.
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central config: OpenRouter, DB, WordPress, and app defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # OpenRouter
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL",
    )
    default_model: str = Field(
        default="openai/gpt-4o",
        description="Default LLM model (e.g. openai/gpt-4o)",
    )
    default_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default LLM temperature",
    )
    default_max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128_000,
        description="Default max completion tokens",
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./content.db",
        description="Database URL (SQLite for dev, PostgreSQL for prod)",
    )

    # WordPress
    wordpress_url: str = Field(default="", description="WordPress site URL")
    wordpress_user: str = Field(default="", description="WordPress username")
    wordpress_app_password: str = Field(default="", description="WordPress application password")
    wordpress_default_status: str = Field(
        default="publish",
        description="Default post status: draft | publish | private",
    )

    # Backend (for Dashboard / external callers)
    backend_url: str = Field(
        default="http://localhost:8000",
        description="Backend API URL for Streamlit etc.",
    )

    @field_validator("wordpress_default_status")
    @classmethod
    def validate_wp_status(cls, v: str) -> str:
        allowed = ("draft", "publish", "private")
        if v.lower() not in allowed:
            raise ValueError(f"Must be one of {allowed}")
        return v.lower()

    @property
    def openrouter_configured(self) -> bool:
        return bool(self.openrouter_api_key.strip())

    @property
    def wordpress_configured(self) -> bool:
        return bool(
            self.wordpress_url.strip()
            and self.wordpress_user.strip()
            and self.wordpress_app_password.strip()
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (load .env once)."""
    return Settings()
