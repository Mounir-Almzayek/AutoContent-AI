"""
APScheduler: schedule publish, one-time generation, and recurring generation jobs.
See docs/10_SCHEDULER_SPEC.md and docs/12_CONTENT_CALENDAR_DESIGN.md.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

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


def _run_recurring_generation(rule_id: int) -> None:
    """Job: run recurring generation for a rule (N articles from keyword queue)."""
    from app.database import SessionLocal
    from sqlalchemy import select
    from models.keyword import Keyword
    from models.article import Article
    from models.schedule_rule import ScheduleRule
    from graphs.content_generation_graph import run_content_generation
    from services.token_tracker import TokenTracker
    from services.wordpress_service import publish_article as wp_publish

    db = SessionLocal()
    try:
        rule = db.get(ScheduleRule, rule_id)
        if not rule or not rule.enabled:
            return
        n = rule.articles_per_run
        if rule.keyword_filter == "ids" and rule.keyword_ids:
            try:
                ids = json.loads(rule.keyword_ids) if rule.keyword_ids.strip().startswith("[") else [int(x.strip()) for x in rule.keyword_ids.split(",") if x.strip()]
            except Exception:
                ids = []
            kw_query = select(Keyword).where(Keyword.id.in_(ids), Keyword.keyword.isnot(None)).limit(n)
        else:
            kw_query = select(Keyword).where(Keyword.status == "pending").order_by(Keyword.created_at).limit(n)
        keywords = list(db.execute(kw_query).scalars().all())
        existing_q = (
            select(Article.id, Article.title, Article.content)
            .where(Article.status.in_(["ready", "published"]))
            .order_by(Article.updated_at.desc())
            .limit(100)
        )
        existing_rows = db.execute(existing_q).all()
        existing_articles = [{"id": r.id, "title": r.title, "content_snippet": (r.content or "")[:500]} for r in existing_rows]
        generated = 0
        for kw in keywords:
            keyword = (kw.keyword or "").strip()
            if not keyword:
                continue
            state = run_content_generation(
                keyword,
                language=rule.language,
                word_count_target=rule.word_count_target,
                tone=rule.tone,
                keyword_id=kw.id,
                existing_articles=existing_articles,
                db_session=db,
            )
            last_usage = state.get("last_usage")
            if last_usage and isinstance(last_usage, dict):
                tracker = TokenTracker(db)
                tracker.log(model="openai/gpt-4o", tokens_prompt=last_usage.get("prompt_tokens", 0), tokens_completion=last_usage.get("completion_tokens", 0), article_id=state.get("article_id"), cost=last_usage.get("total_cost"))
            aid = state.get("article_id")
            if aid:
                generated += 1
                existing_articles.insert(0, {"id": aid, "title": "", "content_snippet": ""})
                if rule.publish_behavior == "immediate":
                    wp_publish(aid, db)
                elif rule.publish_behavior == "delay" and rule.publish_delay_minutes:
                    run_at = datetime.now(timezone.utc) + timedelta(minutes=rule.publish_delay_minutes)
                    schedule_publish(aid, run_at)
        rule.last_run_at = datetime.now(timezone.utc)
        rule.last_articles_count = generated
        db.commit()
        logger.info("Recurring rule %s: generated %s articles", rule_id, generated)
    except Exception as e:
        logger.exception("Recurring generation error: rule_id=%s %s", rule_id, e)
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
        elif job.id and job.id.startswith("recurring_") and len(args) >= 1:
            out.append({"id": job.id, "type": "recurring", "rule_id": args[0], "run_at": run_at, "next_run_time": next_run})
        else:
            out.append({"id": job.id, "type": "unknown", "run_at": run_at, "next_run_time": next_run})
    return out


def add_rule_job(rule: Any) -> str:
    """Add or replace a recurring job for the given rule (ScheduleRule model). Returns job_id."""
    s = get_scheduler()
    job_id = f"recurring_{rule.id}"
    try:
        s.remove_job(job_id)
    except Exception:
        pass
    if rule.trigger_type == "interval" and rule.interval_minutes:
        trigger = IntervalTrigger(minutes=rule.interval_minutes)
    elif rule.trigger_type == "cron" and rule.cron_expression:
        trigger = CronTrigger.from_crontab(rule.cron_expression.strip())
    else:
        raise ValueError("Rule must have interval_minutes or cron_expression")
    job = s.add_job(_run_recurring_generation, trigger, args=[rule.id], id=job_id)
    return job.id


def remove_rule_job(rule_id: int) -> bool:
    """Remove recurring job for rule_id."""
    s = get_scheduler()
    job_id = f"recurring_{rule_id}"
    try:
        s.remove_job(job_id)
        return True
    except Exception:
        return False


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
