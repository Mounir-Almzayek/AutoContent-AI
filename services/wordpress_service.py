"""
WordPress REST API: publish posts and optional categories/tags.
See docs/09_WORDPRESS_INTEGRATION.md.
"""
import base64
import logging
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from models.article import Article

logger = logging.getLogger(__name__)


class WordPressError(Exception):
    """Raised when WordPress API request fails."""

    pass


def _auth_header() -> str:
    """Basic auth header: base64(user:app_password)."""
    s = get_settings()
    raw = f"{s.wordpress_user}:{s.wordpress_app_password}"
    return base64.b64encode(raw.encode()).decode()


def _base_url() -> str:
    """WordPress REST API base URL (no trailing slash)."""
    url = get_settings().wordpress_url.strip().rstrip("/")
    return f"{url}/wp-json/wp/v2"


def publish_article(article_id: int, db: Session) -> dict:
    """
    Publish an article to WordPress. Updates the article record with wordpress_id, published_at, or failure.

    Returns:
        {"ok": True, "wordpress_id": int} or {"ok": False, "error": str}
    """
    settings = get_settings()
    if not settings.wordpress_configured:
        raise WordPressError("WordPress is not configured (URL, user, app password)")

    article = db.get(Article, article_id)
    if not article:
        raise WordPressError("Article not found")

    url = f"{_base_url()}/posts"
    headers = {
        "Authorization": f"Basic {_auth_header()}",
        "Content-Type": "application/json",
    }
    payload = {
        "title": article.title,
        "content": article.content,
        "status": settings.wordpress_default_status,
    }
    if article.meta_description:
        payload["excerpt"] = article.meta_description[:500]

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        err_msg = f"WordPress API error {e.response.status_code}: {e.response.text}"
        logger.exception(err_msg)
        article.status = "failed"
        article.error_message = err_msg[:2000]
        db.commit()
        return {"ok": False, "error": err_msg}
    except Exception as e:
        err_msg = str(e)
        logger.exception("WordPress publish failed: %s", e)
        article.status = "failed"
        article.error_message = err_msg[:2000]
        db.commit()
        return {"ok": False, "error": err_msg}

    wp_id = data.get("id")
    if wp_id is not None:
        from datetime import datetime, timezone
        article.wordpress_id = int(wp_id)
        article.published_at = datetime.now(timezone.utc)
        article.status = "published"
        article.error_message = None
        db.commit()
        db.refresh(article)
        return {"ok": True, "wordpress_id": int(wp_id)}
    return {"ok": False, "error": "WordPress response missing post id"}


def get_categories() -> list[dict]:
    """Fetch WordPress categories (for optional use in Dashboard)."""
    settings = get_settings()
    if not settings.wordpress_configured:
        return []
    url = f"{_base_url()}/categories"
    headers = {"Authorization": f"Basic {_auth_header()}"}
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Failed to fetch WordPress categories: %s", e)
        return []


def get_tags() -> list[dict]:
    """Fetch WordPress tags (for optional use in Dashboard)."""
    settings = get_settings()
    if not settings.wordpress_configured:
        return []
    url = f"{_base_url()}/tags"
    headers = {"Authorization": f"Basic {_auth_header()}"}
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("Failed to fetch WordPress tags: %s", e)
        return []
