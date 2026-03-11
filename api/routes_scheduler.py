"""
Scheduler jobs and stats. Uses APScheduler (scheduler/publisher).
See docs/05_API_DESIGN.md and docs/10_SCHEDULER_SPEC.md.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from api.schemas import ScheduleArticleRequest, ScheduleGenerationRequest
from scheduler.publisher import (
    cancel_job as scheduler_cancel_job,
    list_jobs as scheduler_list_jobs,
    get_stats as scheduler_get_stats,
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
