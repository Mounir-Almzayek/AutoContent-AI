# Scheduler (APScheduler)

## 1. Goals

- Schedule an article to be published at a specific time.
- Schedule content generation for a keyword at a specific time.
- (Optional) Recurring tasks: e.g. review old articles or auto-generate from pending keywords.

Recurring behavior is implemented via **schedule rules** (stored in the DB and re-registered on startup).

---

## 2. Technology

- **APScheduler** (Python library).
- Scheduler type: `BackgroundScheduler` (or `AsyncIOScheduler` if the app is async).
- Storage: in-memory (simple) or a persistent job store (e.g. SQLAlchemy job store or a `scheduled_jobs` table) so jobs survive restarts.

---

## 3. Task Types

| Task | Description | Implementation |
|------|-------------|----------------|
| publish_article | Publish a given article to WordPress at a scheduled time | `wordpress_service.publish_article(article_id)`, then update status and `published_at` |
| generate_content | Run the content pipeline for a keyword at a scheduled time | Invoke LangGraph workflow and save the article |
| Rule-based generation/publish | Recurring rules (e.g. “every day generate from pending keywords” or “publish ready articles”) | `scheduler/publisher.py` registers jobs from `ScheduleRule` rows; rules can target keywords or articles with filters |

---

## 4. Integration with FastAPI

- On startup (`lifespan` or `on_event("startup")`): start the scheduler and re-register all enabled schedule rules from the database.
- On shutdown: shut down the scheduler cleanly.
- The API (see [API Design](../api/design.md)) adds/cancels one-off jobs and manages rules via functions in `scheduler/publisher.py` using the same scheduler instance.

---

## 5. Module `scheduler/publisher.py`

**Responsibilities:**

- Create and hold the scheduler instance.
- Helper functions:
  - `schedule_publish(article_id, run_at: datetime)` → job_id
  - `schedule_generation(keyword_id, run_at: datetime)` → job_id
  - `cancel_job(job_id)`
  - `list_jobs()`
  - `add_rule_job(rule)` — register a recurring job for a `ScheduleRule`
  - `remove_rule_job(rule)` — remove a rule’s job
- Job execution: call WordPress service or run the content generation graph and save the result to the DB.

---

## 6. API Endpoints (Summary)

- **One-off jobs:** GET `/api/v1/scheduler/jobs`, POST `schedule-article`, POST `schedule-generation`, DELETE `jobs/{job_id}`, GET `stats`.
- **Recurring rules:** GET/POST `/api/v1/scheduler/rules`, GET/PATCH/DELETE `rules/{rule_id}`, POST `rules/{rule_id}/pause`, POST `rules/{rule_id}/resume`.
- **Calendar:** GET `/api/v1/scheduler/calendar` for a calendar view of scheduled items.

---

## 7. Persistence After Restart

- If only in-memory jobs are used, restarting the server loses scheduled jobs.
- To persist: use an APScheduler job store (e.g. SQLAlchemyJobStore) or a `scheduled_jobs` table and, on startup, load pending jobs from the DB and add them to the scheduler.
- **Schedule rules** are stored in the `schedule_rules` table; on startup the backend loads enabled rules and calls `add_rule_job(rule)` for each so recurring behavior is restored.
