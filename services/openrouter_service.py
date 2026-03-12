"""
OpenRouter API client for LLM chat completions.
Returns content and usage dict for token tracking.
Retries on 429 (rate limit) with backoff.
See docs/integration/openrouter.md.
"""
import logging
import time
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Retry 429 (rate limit): max attempts, delay in seconds before first retry
MAX_RETRIES_429 = 3
RETRY_DELAY_SECONDS = 5


class OpenRouterError(Exception):
    """Raised when OpenRouter API returns an error or invalid response."""

    pass


class OpenRouterService:
    """Service for calling OpenRouter chat completion API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        default_temperature: Optional[float] = None,
        default_max_tokens: Optional[int] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")
        self.default_model = default_model or settings.default_model
        self.default_temperature = (
            default_temperature if default_temperature is not None else settings.default_temperature
        )
        self.default_max_tokens = (
            default_max_tokens if default_max_tokens is not None else settings.default_max_tokens
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Send chat completion request to OpenRouter.

        Args:
            messages: List of {"role": "user"|"system"|"assistant", "content": "..."}.
            model: Override default model (e.g. openai/gpt-4o).
            temperature: Override default temperature.
            max_tokens: Override default max completion tokens.

        Returns:
            (content, usage) where usage has prompt_tokens, completion_tokens, total_tokens,
            and optionally total_cost if provided by OpenRouter.
        """
        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is not set")

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.default_max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ai-content-system",
        }

        last_error = None
        for attempt in range(1, MAX_RETRIES_429 + 1):
            try:
                with httpx.Client(timeout=300.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code == 429 and attempt < MAX_RETRIES_429:
                        delay = RETRY_DELAY_SECONDS * attempt
                        try:
                            body = resp.json()
                            msg = body.get("error", {}).get("message", "") or resp.text
                            if "rate-limit" in msg.lower() or "rate limited" in msg.lower():
                                logger.warning("OpenRouter 429 rate limit (attempt %s/%s), retry in %ss: %s", attempt, MAX_RETRIES_429, delay, msg[:200])
                        except Exception:
                            logger.warning("OpenRouter 429 (attempt %s/%s), retry in %ss", attempt, MAX_RETRIES_429, delay)
                        time.sleep(delay)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    break
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429 and attempt < MAX_RETRIES_429:
                    delay = RETRY_DELAY_SECONDS * attempt
                    logger.warning("OpenRouter 429, retry in %ss (attempt %s/%s)", delay, attempt, MAX_RETRIES_429)
                    time.sleep(delay)
                    continue
                try:
                    err_body = e.response.json()
                    msg = err_body.get("error", {}).get("message", str(e))
                except Exception:
                    msg = e.response.text or str(e)
                logger.exception("OpenRouter HTTP error: %s", msg)
                raise OpenRouterError(f"OpenRouter API error: {e.response.status_code}. {msg[:300]}") from e
            except Exception as e:
                last_error = e
                logger.exception("OpenRouter request failed: %s", e)
                raise OpenRouterError(str(e)) from e
        else:
            if last_error and isinstance(last_error, httpx.HTTPStatusError) and last_error.response.status_code == 429:
                try:
                    body = last_error.response.json()
                    msg = body.get("error", {}).get("message", "Rate limit exceeded. Try again in a few minutes or use another model.")
                except Exception:
                    msg = "Rate limit (429). Try again later or choose another model in AI Settings."
                raise OpenRouterError(msg) from last_error
            raise OpenRouterError("OpenRouter request failed after retries") from last_error

        choices = data.get("choices")
        if not choices or not isinstance(choices[0].get("message"), dict):
            raise OpenRouterError("Invalid OpenRouter response: missing choices[].message")

        content = choices[0]["message"].get("content") or ""

        usage = data.get("usage") or {}
        usage_dict = {
            "prompt_tokens": int(usage.get("prompt_tokens", 0)),
            "completion_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)),
        }
        if "total_cost" in data:
            usage_dict["total_cost"] = float(data["total_cost"])
        elif "cost" in usage:
            usage_dict["total_cost"] = float(usage["cost"])

        return content, usage_dict


def get_openrouter_service() -> OpenRouterService:
    """Factory for dependency injection (uses app config)."""
    return OpenRouterService()
