# Data Models and Database

## 1. Database

- **Development:** SQLite (single file, no extra setup).
- **Production (recommended):** PostgreSQL.
- **ORM:** SQLAlchemy (models in `models/` or referenced from `app/database.py`).

---

## 2. Articles Table

| Column | Type | Description |
|--------|------|-------------|
| id | PK, auto | Unique ID |
| keyword_id | FK → keywords | Related keyword |
| title | string | Article title |
| content | text | Content (HTML or Markdown) |
| meta_title | string, nullable | Meta title |
| meta_description | string, nullable | Meta description |
| status | enum/string | draft, generating, ready, published, failed |
| seo_score | float, nullable | SEO score from Quality/SEO agents |
| quality_score | float, nullable | Quality score |
| wordpress_id | int, nullable | WordPress post ID after publish |
| published_at | datetime, nullable | Actual publish time |
| created_at | datetime | Created at |
| updated_at | datetime | Last updated |
| error_message | text, nullable | Error message if generation or publish failed |

---

## 3. Keywords Table

| Column | Type | Description |
|--------|------|-------------|
| id | PK, auto | Unique ID |
| keyword | string, unique | Keyword text |
| topic | string, nullable | From Keyword Agent |
| search_intent | string, nullable | informational / transactional / navigational |
| status | enum/string | pending, processed, failed |
| created_at | datetime | Created at |
| updated_at | datetime | Last updated |

---

## 4. Token Usage Table

| Column | Type | Description |
|--------|------|-------------|
| id | PK, auto | Unique ID |
| model | string | Model name (e.g. openai/gpt-4o) |
| tokens_prompt | int | Input tokens |
| tokens_completion | int | Output tokens |
| total_tokens | int | Total |
| cost | decimal, nullable | Cost if available |
| article_id | FK, nullable | Related article if any |
| created_at | datetime | Call time |

---

## 5. Schedule Rules Table (Recurring)

| Column | Type | Description |
|--------|------|-------------|
| id | PK | Rule ID |
| rule_type | string | "keywords" or "articles" |
| keyword_ids / filters | varies | Which keywords or articles (e.g. all_pending) |
| cron / schedule | string | When to run (e.g. cron expression) |
| publish_behavior | string | e.g. immediate or delayed |
| publish_delay_minutes | int, nullable | Delay before publish (if applicable) |
| trend_time_window | string, nullable | For keyword rules (e.g. last week, last month) |
| enabled | bool | Whether the rule is active |
| created_at, updated_at | datetime | Timestamps |

---

## 6. Scheduled Jobs (Optional)

If jobs are persisted (e.g. for restart survival), a table can track them:

| Column | Type | Description |
|--------|------|-------------|
| id | PK | Job ID (or scheduler job_id) |
| type | string | publish / generate |
| article_id | FK, nullable | For publish jobs |
| keyword_id | FK, nullable | For generate jobs |
| scheduled_at | datetime | Planned run time |
| status | string | pending, running, completed, failed, cancelled |
| created_at | datetime | Created at |

---

## 7. Pydantic Schemas (API)

- **ArticleCreate, ArticleUpdate, ArticleResponse** — Articles.
- **KeywordCreate, KeywordResponse, KeywordUpdate** — Keywords.
- **GenerateRequest, GenerateResponse** — POST /articles/generate.
- **TokenUsageResponse, UsageSummary** — /usage/tokens, /usage/by-article.
- **AISettingsPerAgent, AISettingsUpdate** — GET/PATCH /settings/ai.
- **ScheduleRuleCreate, ScheduleRuleUpdate, ScheduleRuleResponse** — Scheduler rules.
- **ScheduleArticleRequest, ScheduleGenerationRequest** — One-off schedule endpoints.
- **TrendDiscoveryRequest, TrendDiscoveryResponse, ImportFromTrendsRequest** — Trend discovery and import.

Schemas live in `api/schemas.py`; DB models in `models/` (e.g. `article.py`, `keyword.py`, `schedule_rule.py`, `token_usage.py`).
