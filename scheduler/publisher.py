"""
APScheduler: schedule publish and content generation jobs.
See docs/10_SCHEDULER_SPEC.md.
"""
import logging
from datetime import datetime
from typing import Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def _run_publish(article_id: int) -> None:
    """Job: publish one article to WordPress."""
    from app.database import SessionLocal
    from services.wordpress_service import publish_article as wp_publish, WordPressError

    db = SessionLocal()
    try:
        result = wp_publish(article_id, db)
        if result.get("ok"):
            logger.info("Scheduled publish completed: article_id=%s wordpress_id=%s", article_id, result.get("wordpress_id"))
        else:
            logger.warning("Scheduled publish failed: article_id=%s error=%s", article_id, result.get("error"))
    except WordPressError as e:
        logger.exception("Scheduled publish error: %s", e)
    finally:
        db.close()


def _run_generation(keyword_id: int) -> None:
    """Job: run content generation for one keyword."""
    from app.database import SessionLocal
    from sqlalchemy import select
    from models.keyword import Keyword
    from models.article import Article
    from graphs.content_generation_graph import run_content_generation
    from services.token_tracker import TokenTracker

    db = SessionLocal()
    try:
        kw = db.get(Keyword, keyword_id)
        if not kw:
            logger.warning("Scheduled generation: keyword_id=%s not found", keyword_id)
            return
        keyword = kw.keyword.strip()
        if not keyword:
            return
        existing_q = (
            select(Article.id, Article.title, Article.content)
            .where(Article.status.in_(["ready", "published"]))
            .order_by(Article.updated_at.desc())
            .limit(100)
        )
        existing_rows = db.execute(existing_q).all()
        existing_articles = [
            {"id": r.id, "title": r.title, "content_snippet": (r.content or "")[:500]}
            for r in existing_rows
        ]
        state = run_content_generation(
            keyword,
            language="en",
            word_count_target=1500,
            tone="professional",
            keyword_id=keyword_id,
            existing_articles=existing_articles,
            db_session=db,
        )
        last_usage = state.get("last_usage")
        if last_usage and isinstance(last_usage, dict):
            tracker = TokenTracker(db)
            tracker.log(
                model="openai/gpt-4o",
                tokens_prompt=last_usage.get("prompt_tokens", 0),
                tokens_completion=last_usage.get("completion_tokens", 0),
                article_id=state.get("article_id"),
                cost=last_usage.get("total_cost"),
            )
        if state.get("error"):
            logger.warning("Scheduled generation failed: keyword_id=%s error=%s", keyword_id, state.get("error"))
        elif state.get("article_id"):
            logger.info("Scheduled generation completed: keyword_id=%s article_id=%s", keyword_id, state.get("article_id"))
    except Exception as e:
        logger.exception("Scheduled generation error: keyword_id=%s %s", keyword_id, e)
    finally:
        db.close()


def get_scheduler() -> BackgroundScheduler:
    """Return the global scheduler instance; create and start if needed."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()
        logger.info("APScheduler started")
    return _scheduler


def schedule_publish(article_id: int, run_at: datetime) -> str:
    """Schedule an article to be published at run_at. Returns job_id."""
    import uuid
    s = get_scheduler()
    job_id = f"publish_{article_id}_{run_at.timestamp()}_{uuid.uuid4().hex[:8]}"
    job = s.add_job(_run_publish, "date", run_date=run_at, args=[article_id], id=job_id)
    return job.id


def schedule_generation(keyword_id: int, run_at: datetime) -> str:
    """Schedule content generation for a keyword at run_at. Returns job_id."""
    import uuid
    s = get_scheduler()
    job_id = f"gen_{keyword_id}_{run_at.timestamp()}_{uuid.uuid4().hex[:8]}"
    job = s.add_job(_run_generation, "date", run_date=run_at, args=[keyword_id], id=job_id)
    return job.id


def cancel_job(job_id: str) -> bool:
    """Remove a scheduled job. Returns True if removed."""
    s = get_scheduler()
    try:
        s.remove_job(job_id)
        return True
    except Exception:
        return False


def list_jobs() -> list[dict[str, Any]]:
    """List all scheduled jobs with id, type, run_at, next_run_time."""
    s = get_scheduler()
    out = []
    for job in s.get_jobs():
        args = list(job.args or [])
        run_date = getattr(getattr(job, "trigger", None), "run_date", None)
        run_at = run_date.isoformat() if run_date and getattr(run_date, "isoformat", None) else None
        next_run = job.next_run_time.isoformat() if job.next_run_time and getattr(job.next_run_time, "isoformat", None) else None
        if job.id and job.id.startswith("publish_") and len(args) >= 1:
            out.append({"id": job.id, "type": "publish", "article_id": args[0], "run_at": run_at, "next_run_time": next_run})
        elif job.id and job.id.startswith("gen_") and len(args) >= 1:
            out.append({"id": job.id, "type": "generate", "keyword_id": args[0], "run_at": run_at, "next_run_time": next_run})
        else:
            out.append({"id": job.id, "type": "unknown", "run_at": run_at, "next_run_time": next_run})
    return out


def get_stats() -> dict[str, Any]:
    """Scheduler stats: total_jobs, next_run (soonest next run)."""
    jobs = list_jobs()
    next_run = None
    for j in jobs:
        nr = j.get("next_run_time")
        if nr and (next_run is None or nr < next_run):
            next_run = nr
    return {"total_jobs": len(jobs), "next_run": next_run}


def shutdown_scheduler() -> None:
    """Stop the scheduler (e.g. on app shutdown)."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler shut down")
