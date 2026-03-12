# FastAPI API Design

## 1. General Conventions

- **Base URL:** `/api/v1`
- **Documentation:** Swagger UI at `/docs`, ReDoc at `/redoc`
- **Responses:** Pydantic models for all responses (lists, single item, error messages)

---

## 2. Articles

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/articles` | List articles (query: status, from_date, to_date, skip, limit) |
| GET | `/articles/{article_id}` | Get one article |
| POST | `/articles` | Create article manually (no AI) |
| POST | `/articles/generate` | Run generation pipeline (body: keyword, options) |
| PATCH | `/articles/{article_id}` | Update (e.g. status, title, content) |
| DELETE | `/articles/{article_id}` | Delete article |
| POST | `/articles/{article_id}/publish` | Publish article to WordPress |

**Example body for POST /articles/generate:**

```json
{
  "keyword": "best digital marketing tools",
  "options": {
    "language": "en",
    "tone": "professional",
    "word_count_target": 1500,
    "model_override": "openai/gpt-4o"
  }
}
```

---

## 3. Keywords

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/keywords` | List keywords (query: status, q, skip, limit) |
| GET | `/keywords/{keyword_id}` | Get one keyword |
| POST | `/keywords` | Add one keyword |
| POST | `/keywords/import` | Import from file (multipart: csv/txt, one per line or comma-separated) |
| PATCH | `/keywords/{keyword_id}` | Update keyword |
| DELETE | `/keywords/{keyword_id}` | Delete keyword |
| POST | `/keywords/trend-discovery` | Discover trends and generate keyword/idea batch (body: niche, language, etc.) |
| POST | `/keywords/import-from-trends` | Import selected items from trend discovery as keywords |

---

## 4. Scheduler

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/scheduler/jobs` | List scheduled jobs |
| POST | `/scheduler/schedule-article` | Schedule article publish (body: article_id, scheduled_at ISO 8601) |
| POST | `/scheduler/schedule-generation` | Schedule generation for keyword (body: keyword_id, scheduled_at) |
| DELETE | `/scheduler/jobs/{job_id}` | Cancel a job |
| GET | `/scheduler/stats` | Scheduler stats (count, next run, etc.) |
| GET | `/scheduler/rules` | List all recurring schedule rules |
| POST | `/scheduler/rules` | Create a recurring rule (articles or keywords) |
| GET | `/scheduler/rules/{rule_id}` | Get one rule |
| PATCH | `/scheduler/rules/{rule_id}` | Update rule |
| DELETE | `/scheduler/rules/{rule_id}` | Delete rule |
| POST | `/scheduler/rules/{rule_id}/pause` | Pause rule |
| POST | `/scheduler/rules/{rule_id}/resume` | Resume rule |
| GET | `/scheduler/calendar` | Calendar view (articles and events by date) |

---

## 5. Token Usage and AI Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/usage/tokens` | Token usage (query: period=day\|week\|month, or from/to) |
| GET | `/usage/by-article` | Usage per article (optional query params) |
| GET | `/settings/ai` | Current AI settings (per-agent model, temperature, max_tokens) |
| PATCH | `/settings/ai` | Update AI settings |

---

## 6. Health and Readiness

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health (DB connectivity; optional OpenRouter check) |
| GET | `/ready` | Readiness for traffic |

---

## 7. Wiring in app/main.py

- Include routers from `api/routes_articles`, `routes_keywords`, `routes_scheduler`, `routes_usage`, `routes_settings`.
- Use prefix `prefix="/api/v1"`.
- Use tags in OpenAPI: Articles, Keywords, Scheduler, Usage, Settings.

Request/response schemas are defined in `api/schemas.py` and models in [Data Models](../data/models.md).
