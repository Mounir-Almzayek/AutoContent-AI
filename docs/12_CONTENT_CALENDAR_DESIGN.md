# 12 — Content Calendar: Design & Implementation

Professional content calendar for automated generation and publishing. Production SaaS–oriented.

---

## 1. UX Design Recommendations

### 1.1 Information hierarchy
- **Primary:** When things happen (calendar/timeline) and what is scheduled (jobs list).
- **Secondary:** Recurring rules and one-time schedule forms.
- **Tertiary:** System feedback (next run, last run, counts).

### 1.2 Views
- **Calendar / timeline:** Month or week view with dots or bars for scheduled publish and generation times; click opens detail or edit.
- **Job list:** Table with Type, Target (article/keyword), Run at, Status, Actions (Pause/Resume/Edit/Delete). Use `st.data_editor` or cards for dense data.
- **Recurring rules:** Cards per rule with summary (e.g. "Every 6h, 2 articles, publish immediately") and Edit/Enable/Disable/Delete.

### 1.3 Workflow clarity
- **One-time:** "Schedule publish" and "Schedule generation" stay as clear forms with date/time picker.
- **Recurring:** Single "Add recurring rule" flow: trigger (interval/cron) → generation settings (N articles, keyword source, language, tone, length) → publishing (immediate / delayed / draft only).
- **Instant automation:** Toggle or radio: "Publish immediately after generation" | "Publish at [time]" | "Save as draft only."

### 1.4 Feedback
- **Metrics row:** Next run, Last run, Active jobs, Articles generated (today/week).
- **Status:** Per job: active / paused / failed. Use `st.status` for long-running or multi-step feedback where applicable.
- **Toasts:** "Rule created", "Job paused", "Job deleted" for non-blocking confirmation.

---

## 2. Streamlit Layout Structure

```
Content Calendar (title)
├── Metrics row [Next run | Last run | Active jobs | Generated (period)]
├── Tabs
│   ├── Calendar view
│   │   ├── Month/week selector (date_input or selectbox)
│   │   ├── Grid or list of days with scheduled items (publish + generation)
│   │   └── Click → detail or side panel
│   ├── One-time schedule
│   │   ├── Schedule publish (article + datetime)
│   │   └── Schedule generation (keyword + datetime)
│   ├── Recurring rules
│   │   ├── List of rules (cards or table)
│   │   └── Form: Add/Edit rule (interval/cron, N articles, keywords, options, publish behavior)
│   ├── Job management
│   │   ├── Table: Job ID, Type, Target, Run at, Status, Actions
│   │   └── Pause / Resume / Delete
│   └── System
│       ├── Scheduler status (active/paused)
│       └── Last run times, failure count
```

Use **st.tabs**, **st.columns** for metrics and two-column forms, **st.expander** for optional fields, **st.metric** for KPIs, **st.status** for "Running…" where useful, **st.toast** for success.

---

## 3. Backend Scheduling Logic

### 3.1 Job types
| Type | Trigger | Payload | Description |
|------|--------|--------|-------------|
| **one_time_publish** | date | article_id | Publish one article at run_at (existing). |
| **one_time_generate** | date | keyword_id | Generate one article at run_at (existing). |
| **recurring_generate** | interval or cron | rule_id | Every X or cron: pick N pending keywords, generate, optionally schedule publish or publish immediately. |
| **recurring_publish** | cron (optional) | — | Publish all "ready" scheduled for this slot (optional future). |

### 3.2 Recurring generation flow
1. Load rule by `rule_id`: interval_or_cron, articles_per_run, keyword_filter (all pending / specific IDs), language, tone, word_count_target, publish_behavior (draft | immediate | delay_minutes).
2. Select up to N keywords (status=pending or from rule’s keyword_ids).
3. For each keyword: run `run_content_generation(…)`, save article (draft/ready).
4. If publish_behavior == immediate: for each new article call `schedule_publish(article_id, now)` or call WordPress publish now.
5. If publish_behavior == delay_minutes: schedule_publish(article_id, now + delay).
6. If draft: leave status ready, no schedule.
7. Update keyword status to processed (optional).
8. Record last_run_time, articles_generated on the rule (DB or in-memory).

### 3.3 Pause / resume
- **Pause:** Remove job from APScheduler (or don’t re-add after run). Persist "paused" in DB for rule.
- **Resume:** Re-add job to scheduler with same trigger and args (rule_id). Set "active" in DB.

---

## 4. APScheduler Job Design

### 4.1 Triggers
- **DateTrigger:** One-time publish, one-time generate (existing).
- **IntervalTrigger:** Recurring generation every X hours/days (e.g. every 6 hours).
- **CronTrigger:** Recurring at specific times (e.g. daily at 09:00).

### 4.2 Job IDs
- One-time: `publish_{article_id}_{ts}_{uuid}`, `gen_{keyword_id}_{ts}_{uuid}` (existing).
- Recurring: `recurring_{rule_id}` so we can pause/resume by rule_id.

### 4.3 Runner
- `_run_recurring_generation(rule_id: int)`:
  - Open DB, load rule (rule_id).
  - If rule.enabled == False, return.
  - Select N keywords (by rule’s keyword_ids or status=pending).
  - For each: run_content_generation(…), then handle publish_behavior.
  - Update rule.last_run_at, rule.last_articles_count (if we have a rule table).
  - Close DB.

### 4.4 Persistence
- Use **SQLAlchemyJobStore** (same DB) so jobs survive restart. Or store only rules in DB and re-create scheduler jobs on startup from rules (simpler: rules in DB, jobs in memory; on startup load rules and add_job for each enabled rule).

---

## 5. API Endpoints Needed

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/scheduler/jobs | List all jobs (one-time + recurring). Extend response with job_type, rule_id if recurring. |
| GET | /api/v1/scheduler/stats | Add last_run, articles_generated_today, etc. |
| POST | /api/v1/scheduler/schedule-article | (existing) |
| POST | /api/v1/scheduler/schedule-generation | (existing) |
| DELETE | /api/v1/scheduler/jobs/{job_id} | (existing) |
| POST | /api/v1/scheduler/jobs/{job_id}/pause | Pause (remove from scheduler, mark paused in store). |
| POST | /api/v1/scheduler/jobs/{job_id}/resume | Resume (re-add job). |
| GET | /api/v1/scheduler/calendar | Query param: start_date, end_date. Returns events: scheduled publishes, scheduled generations, and optionally "generated" events from history. |
| GET | /api/v1/scheduler/rules | List recurring rules. |
| GET | /api/v1/scheduler/rules/{id} | Get one rule. |
| POST | /api/v1/scheduler/rules | Create recurring rule (interval or cron, options, publish_behavior). Creates APScheduler job. |
| PATCH | /api/v1/scheduler/rules/{id} | Update rule; replace scheduler job. |
| DELETE | /api/v1/scheduler/rules/{id} | Delete rule; remove job. |
| POST | /api/v1/scheduler/rules/{id}/pause | Pause rule (disable job). |
| POST | /api/v1/scheduler/rules/{id}/resume | Resume rule. |

---

## 6. Database Schema Suggestions

### 6.1 schedule_rule (recurring generation rules)
| Column | Type | Description |
|--------|------|-------------|
| id | PK | |
| name | string | User-facing name (e.g. "Daily SEO batch") |
| trigger_type | string | interval | cron |
| interval_minutes | int, nullable | For interval: every N minutes (e.g. 360 = 6h) |
| cron_expression | string, nullable | e.g. "0 9 * * *" (daily 09:00) |
| articles_per_run | int | N articles per run (default 1) |
| keyword_filter | string | all_pending | ids |
| keyword_ids | JSON/Text, nullable | Comma or JSON array of keyword IDs if keyword_filter=ids |
| language | string | |
| tone | string | |
| word_count_target | int | |
| publish_behavior | string | draft | immediate | delay |
| publish_delay_minutes | int, nullable | If delay, how many minutes after generation |
| enabled | bool | If false, job not added to scheduler |
| last_run_at | datetime, nullable | |
| last_articles_count | int, nullable | |
| created_at | datetime | |
| updated_at | datetime | |

### 6.2 job_run_history (optional, for "last run" and counts)
| Column | Type | Description |
|--------|------|-------------|
| id | PK | |
| job_type | string | one_time_publish | one_time_generate | recurring_generate |
| rule_id | FK, nullable | For recurring |
| article_id | FK, nullable | For publish |
| keyword_id | FK, nullable | For generate |
| scheduled_at | datetime | |
| ran_at | datetime | |
| status | string | success | failed |
| error_message | text, nullable | |

---

## 7. Example Job Configuration

### 7.1 Recurring: generate every 6 hours, publish immediately
```json
{
  "name": "Every 6h — auto-publish",
  "trigger_type": "interval",
  "interval_minutes": 360,
  "articles_per_run": 2,
  "keyword_filter": "all_pending",
  "language": "en",
  "tone": "professional",
  "word_count_target": 1500,
  "publish_behavior": "immediate",
  "enabled": true
}
```

### 7.2 Recurring: daily at 9:00, save as draft
```json
{
  "name": "Daily draft batch",
  "trigger_type": "cron",
  "cron_expression": "0 9 * * *",
  "articles_per_run": 3,
  "keyword_filter": "all_pending",
  "publish_behavior": "draft",
  "enabled": true
}
```

### 7.3 Recurring: every 12 hours, publish 30 minutes after generation
```json
{
  "name": "Twice daily — delayed publish",
  "trigger_type": "interval",
  "interval_minutes": 720,
  "articles_per_run": 1,
  "publish_behavior": "delay",
  "publish_delay_minutes": 30,
  "enabled": true
}
```

---

## 8. Workflow Summary

```
Keyword selection (manual or from queue)
    → AI article generation (LangGraph)
    → Content quality check (in pipeline)
    → Save draft (status=ready)
    → [Optional] Schedule publishing (one-time or from rule)
    → Publish to WordPress
```

Recurring rules automate: **keyword selection** (from pending or list) → **generation** → **draft** → **publish behavior** (draft / immediate / delay). One-time jobs remain for single article or single publish at a chosen time.
