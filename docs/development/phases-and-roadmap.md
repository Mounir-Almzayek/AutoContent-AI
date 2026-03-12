# Phases and Roadmap

## 1. Phase Overview

| Phase | Name | Main goal | Outputs |
|-------|------|-----------|---------|
| **0** | Structure and docs | Project layout + documentation | Folders, files, docs |
| **1** | Foundation (Config, DB, OpenRouter) | Running environment and LLM connection | config, DB, openrouter_service, token_tracker |
| **2** | Agents and Graph | Node and workflow implementation | agents/*, graphs/* |
| **3** | Backend API | FastAPI + routes | app/main, api/*, models |
| **4** | Scheduling and WordPress | Publishing and scheduling | scheduler/*, wordpress_service |
| **5** | Dashboard | Streamlit UI | dashboard/* |
| **6** | Polish and testing | Quality, monitoring, documentation | tests, improvements |

---

## 2. Full File and Folder Layout

```
ai-content-system/
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings (env, model, etc.)
│   └── database.py          # DB connection and tables
│
├── api/
│   ├── __init__.py
│   ├── routes_articles.py   # Article CRUD + generation
│   ├── routes_keywords.py   # Keyword management
│   ├── routes_scheduler.py  # Scheduling and jobs
│   ├── routes_settings.py   # AI settings
│   ├── routes_usage.py      # Token usage
│   └── schemas.py           # Pydantic schemas
│
├── agents/
│   ├── __init__.py
│   ├── keyword_agent.py
│   ├── brief_agent.py
│   ├── article_agent.py
│   ├── quality_agent.py
│   ├── duplicate_agent.py
│   ├── seo_agent.py
│   └── trend_agent.py        # Trend discovery
│
├── graphs/
│   ├── __init__.py
│   └── content_generation_graph.py
│
├── services/
│   ├── __init__.py
│   ├── openrouter_service.py   # OpenRouter calls
│   ├── wordpress_service.py    # Publish to WordPress
│   ├── token_tracker.py        # Token recording and queries
│   ├── agent_settings.py       # Per-agent AI settings
│   └── web_search.py           # Trend discovery (e.g. DuckDuckGo)
│
├── scheduler/
│   ├── __init__.py
│   └── publisher.py            # Publish and generation jobs
│
├── dashboard/
│   ├── __init__.py
│   └── streamlit_app.py        # Streamlit app
│
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── article.py              # Article model (DB + Pydantic)
│   ├── keyword.py              # Keyword model
│   ├── schedule_rule.py        # Recurring rules
│   └── token_usage.py          # Token usage model
│
├── docs/                        # Documentation
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Files by Phase

### Phase 0 — Structure and docs

- Create the folders above.
- Create all `docs/` files.
- Add `requirements.txt`, `.env.example`, and a basic `README.md`.
- Add `__init__.py` in each package.

### Phase 1 — Foundation

| File | Purpose |
|------|---------|
| `app/config.py` | Read env (OPENROUTER_API_KEY, DB_URL, WORDPRESS_*, etc.) |
| `app/database.py` | SQLAlchemy engine, session, table definitions (or import from models) |
| `models/article.py` | Article table/model + Pydantic schemas |
| `models/keyword.py` | Keyword table/model + Pydantic |
| `services/openrouter_service.py` | LLM chat completion via OpenRouter |
| `services/token_tracker.py` | Record (model, tokens_in, tokens_out, cost, timestamp) and query stats |

### Phase 2 — Agents and Graph

| File | Purpose |
|------|---------|
| `agents/keyword_agent.py` | Keyword Agent logic and OpenRouter call |
| `agents/brief_agent.py` | Content Brief logic |
| `agents/article_agent.py` | Article generation |
| `agents/quality_agent.py` | Quality check and scores |
| `agents/duplicate_agent.py` | Embedding or title comparison |
| `agents/seo_agent.py` | SEO and meta optimization |
| `graphs/content_generation_graph.py` | State, nodes, edges, conditional, compile |

### Phase 3 — Backend API

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, CORS, include routers |
| `api/routes_articles.py` | POST/GET/PATCH articles, run pipeline |
| `api/routes_keywords.py` | Keyword CRUD, import, trend discovery |
| `api/routes_scheduler.py` | Jobs, rules, calendar |
| `api/routes_settings.py` | AI settings |
| `api/routes_usage.py` | Token usage |

### Phase 4 — Scheduling and WordPress

| File | Purpose |
|------|---------|
| `services/wordpress_service.py` | POST /wp/v2/posts, site config |
| `scheduler/publisher.py` | APScheduler, publish_article, generate_content, rule jobs |

### Phase 5 — Dashboard

| File | Purpose |
|------|---------|
| `dashboard/streamlit_app.py` | Pages: Articles, Keywords, Token Usage, AI Settings, Content Calendar |

### Phase 6 — Polish

- Add `tests/` and unit/integration tests.
- Improve error handling and logging.
- Document API (OpenAPI) and link to docs.

---

## 4. Recommended Development Order

1. **0** → Create structure and docs (as documented here).
2. **1** → config, database, models, openrouter_service, token_tracker.
3. **2** → Agents one by one, then the graph.
4. **3** → main + routes (articles first, then keywords, then scheduler, settings, usage).
5. **4** → wordpress_service then scheduler.
6. **5** → Dashboard wired to the API.
7. **6** → Tests and improvements.

---

## 5. Dependencies (requirements.txt summary)

- `fastapi`, `uvicorn`
- `streamlit`
- `langgraph`, `langchain-core`
- `httpx` (OpenRouter, WordPress)
- `sqlalchemy`, DB driver (e.g. `asyncpg` if using async)
- `apscheduler`
- `pydantic`, `pydantic-settings`
- `python-dotenv`
- `ddgs` (trend discovery)
- (Optional) `sentence-transformers` or embeddings library for duplicate check

Details in the linked docs (API, data models, OpenRouter, etc.).
