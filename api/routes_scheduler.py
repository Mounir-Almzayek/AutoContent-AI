"""
Scheduler jobs and stats. Stub implementation until Phase 4 (APScheduler).
See docs/05_API_DESIGN.md and docs/10_SCHEDULER_SPEC.md.
"""
from fastapi import APIRouter, HTTPException

from api.schemas import ScheduleArticleRequest, ScheduleGenerationRequest

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.get("/jobs", response_model=dict)
def list_jobs():
    """List scheduled jobs. Full implementation in Phase 4."""
    return {"jobs": [], "total": 0}


@router.post("/schedule-article")
def schedule_article(body: ScheduleArticleRequest):
    """Schedule an article for publishing at a given time. Implemented in Phase 4."""
    raise HTTPException(
        status_code=501,
        detail="Scheduler will be implemented in Phase 4 (APScheduler)",
    )


@router.post("/schedule-generation")
def schedule_generation(body: ScheduleGenerationRequest):
    """Schedule content generation for a keyword at a given time. Implemented in Phase 4."""
    raise HTTPException(
        status_code=501,
        detail="Scheduler will be implemented in Phase 4 (APScheduler)",
    )


@router.delete("/jobs/{job_id}", status_code=204)
def cancel_job(job_id: str):
    """Cancel a scheduled job. Implemented in Phase 4."""
    raise HTTPException(
        status_code=501,
        detail="Scheduler will be implemented in Phase 4 (APScheduler)",
    )


@router.get("/stats", response_model=dict)
def scheduler_stats():
    """Scheduler statistics. Implemented in Phase 4."""
    return {"total_jobs": 0, "next_run": None}
