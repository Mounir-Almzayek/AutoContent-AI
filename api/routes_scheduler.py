"""
Scheduler jobs, stats, recurring rules, and calendar. See docs/10_SCHEDULER_SPEC.md and docs/12_CONTENT_CALENDAR_DESIGN.md.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from api.schemas import ScheduleArticleRequest, ScheduleGenerationRequest
from models.schedule_rule import ScheduleRule, ScheduleRuleCreate, ScheduleRuleResponse, ScheduleRuleUpdate
from models.article import Article
from scheduler.publisher import (
    add_rule_job,
    cancel_job as scheduler_cancel_job,
    list_jobs as scheduler_list_jobs,
    get_stats as scheduler_get_stats,
    remove_rule_job,
    schedule_generation as scheduler_schedule_generation,
    schedule_publish as scheduler_schedule_publish,
)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


def _parse_iso(s: str) -> datetime:
    """Parse ISO 8601 datetime string."""
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid scheduled_at (use ISO 8601): {e}") from e


@router.get("/jobs", response_model=dict)
def list_jobs():
    """List scheduled jobs."""
    jobs = scheduler_list_jobs()
    return {"jobs": jobs, "total": len(jobs)}


@router.post("/schedule-article")
def schedule_article(body: ScheduleArticleRequest):
    """Schedule an article for publishing at a given time."""
    run_at = _parse_iso(body.scheduled_at)
    now = datetime.now(run_at.tzinfo) if run_at.tzinfo else datetime.now(timezone.utc)
    if run_at <= now:
        raise HTTPException(status_code=400, detail="scheduled_at must be in the future")
    job_id = scheduler_schedule_publish(body.article_id, run_at)
    return {"job_id": job_id, "article_id": body.article_id, "scheduled_at": run_at.isoformat()}


@router.post("/schedule-generation")
def schedule_generation(body: ScheduleGenerationRequest):
    """Schedule content generation for a keyword at a given time."""
    run_at = _parse_iso(body.scheduled_at)
    now = datetime.now(run_at.tzinfo) if run_at.tzinfo else datetime.now(timezone.utc)
    if run_at <= now:
        raise HTTPException(status_code=400, detail="scheduled_at must be in the future")
    job_id = scheduler_schedule_generation(body.keyword_id, run_at)
    return {"job_id": job_id, "keyword_id": body.keyword_id, "scheduled_at": run_at.isoformat()}


@router.delete("/jobs/{job_id}", status_code=204)
def cancel_job(job_id: str):
    """Cancel a scheduled job."""
    if not scheduler_cancel_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found or already run")
    return None


@router.get("/stats", response_model=dict)
def scheduler_stats():
    """Scheduler statistics."""
    return scheduler_get_stats()


# ---------- Recurring rules ----------


@router.get("/rules", response_model=list)
def list_rules(db: Session = Depends(get_db)):
    """List all schedule rules."""
    rows = db.execute(select(ScheduleRule).order_by(ScheduleRule.created_at.desc())).scalars().all()
    return [ScheduleRuleResponse.model_validate(r) for r in rows]


@router.post("/rules", response_model=ScheduleRuleResponse)
def create_rule(body: ScheduleRuleCreate, db: Session = Depends(get_db)):
    """Create a recurring schedule rule and register its job."""
    data = body.model_dump(exclude_unset=True)
    if data.get("rule_type") == "articles":
        data["keyword_filter"] = "all_pending"
        data["publish_behavior"] = "immediate"
        data.pop("keyword_ids", None)
        data["publish_delay_minutes"] = None
    rule = ScheduleRule(**data)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    if rule.enabled:
        add_rule_job(rule)
    return ScheduleRuleResponse.model_validate(rule)


@router.get("/rules/{rule_id}", response_model=ScheduleRuleResponse)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a schedule rule by id."""
    rule = db.get(ScheduleRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return ScheduleRuleResponse.model_validate(rule)


@router.patch("/rules/{rule_id}", response_model=ScheduleRuleResponse)
def update_rule(rule_id: int, body: ScheduleRuleUpdate, db: Session = Depends(get_db)):
    """Update a schedule rule; resets the job if trigger changed."""
    rule = db.get(ScheduleRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    data = body.model_dump(exclude_unset=True)
    if rule.rule_type == "articles":
        data.pop("keyword_filter", None)
        data.pop("keyword_ids", None)
        data["keyword_filter"] = "all_pending"
        data["publish_behavior"] = "immediate"
        data["publish_delay_minutes"] = None
    for k, v in data.items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    remove_rule_job(rule_id)
    if rule.enabled:
        add_rule_job(rule)
    return ScheduleRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete a schedule rule and remove its job."""
    rule = db.get(ScheduleRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    remove_rule_job(rule_id)
    db.delete(rule)
    db.commit()
    return None


@router.post("/rules/{rule_id}/pause", response_model=ScheduleRuleResponse)
def pause_rule(rule_id: int, db: Session = Depends(get_db)):
    """Disable rule and remove its scheduled job."""
    rule = db.get(ScheduleRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    remove_rule_job(rule_id)
    rule.enabled = False
    db.commit()
    db.refresh(rule)
    return ScheduleRuleResponse.model_validate(rule)


@router.post("/rules/{rule_id}/resume", response_model=ScheduleRuleResponse)
def resume_rule(rule_id: int, db: Session = Depends(get_db)):
    """Enable rule and re-register its job."""
    rule = db.get(ScheduleRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.enabled = True
    db.commit()
    db.refresh(rule)
    add_rule_job(rule)
    return ScheduleRuleResponse.model_validate(rule)


# ---------- Calendar ----------


@router.get("/calendar", response_model=dict)
def get_calendar(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return calendar events: scheduled jobs and articles (scheduled/published) in the date range."""
    tz = timezone.utc
    try:
        start = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if start_date else datetime.now(tz)
        end = datetime.fromisoformat(end_date.replace("Z", "+00:00")) if end_date else (start + timedelta(days=31))
    except (ValueError, TypeError):
        start = datetime.now(tz)
        end = start + timedelta(days=31)
    if start > end:
        start, end = end, start

    events = []
    jobs = scheduler_list_jobs()
    for j in jobs:
        run_at = j.get("run_at") or j.get("next_run_time")
        if not run_at:
            continue
        if isinstance(run_at, str):
            run_at = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
        if start <= run_at <= end:
            events.append({
                "type": "job",
                "id": j.get("id"),
                "job_type": j.get("type"),
                "run_at": run_at.isoformat() if hasattr(run_at, "isoformat") else str(run_at),
                "article_id": j.get("article_id"),
                "keyword_id": j.get("keyword_id"),
                "rule_id": j.get("rule_id"),
            })

    # Articles with published_at in range (scheduled publish is represented by jobs above)
    q = db.execute(
        select(Article).where(
            Article.published_at.isnot(None),
            Article.published_at >= start,
            Article.published_at <= end,
        )
    ).scalars().all()
    for a in q:
        if a.published_at and start <= a.published_at <= end:
            events.append({
                "type": "article",
                "id": a.id,
                "article_id": a.id,
                "run_at": a.published_at.isoformat(),
                "status": "published",
                "title": getattr(a, "title", None),
            })

    events.sort(key=lambda e: e.get("run_at") or "")
    return {"events": events, "start": start.isoformat(), "end": end.isoformat()}
