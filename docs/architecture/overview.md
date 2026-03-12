# Architecture Overview

## 1. Main Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    Dashboard (Streamlit)                          │
│  Keywords | Scheduling | LLM Settings | Token Usage Monitoring   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP / REST API
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Backend Service (FastAPI)                        │
│  API | DB Management | Workflow Execution | Scheduling | WordPress │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Internal calls
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              AI Engine (LangGraph + OpenRouter)                  │
│  Graph: Keyword → Brief → Article → Quality → Duplicate → SEO   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│              WordPress API + Database (SQLite/PostgreSQL)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Responsibilities

### 2.1 Control Interface (Streamlit Dashboard)

| Function | Description |
|----------|-------------|
| Keyword management | Add, edit, delete, import keywords |
| Article scheduling | Content calendar and publish-time selection |
| LLM model selection | From OpenRouter list (GPT-4, Claude, Mixtral, etc.) |
| Article status tracking | Draft, generating, published, failed |
| Token usage monitoring | Daily, weekly, monthly, per-article |
| Analytics | Article counts, publish rate, SEO quality |

### 2.2 Service Layer (FastAPI Backend)

| Function | Description |
|----------|-------------|
| Dashboard API | All CRUD and operations via REST |
| Database management | Articles, keywords, scheduling, tokens |
| AI workflow execution | Invokes LangGraph and runs the pipeline |
| Publish scheduling | APScheduler for publish and generation jobs |
| WordPress integration | Publishes articles via REST API |

### 2.3 AI Engine (LangGraph + OpenRouter)

| Function | Description |
|----------|-------------|
| Pipeline execution | Runs nodes in order with shared state |
| LLM calls | Via OpenRouter (configurable model) |
| Token tracking | Records usage per call |
| Error handling | Retry, fallback, logging |

---

## 3. Data Flow

1. **User** adds a keyword or selects an article from the dashboard.
2. **Backend** receives the request and invokes the AI engine (LangGraph).
3. **AI engine** runs: Keyword → Brief → Article → Quality → Duplicate → SEO.
4. **Backend** saves the article to the DB and updates status.
5. **Scheduler** (or user) triggers publish to WordPress.
6. **WordPress service** sends `POST /wp/v2/posts` and updates article status to "published".

---

## 4. Technology Stack

| Component | Technology |
|-----------|------------|
| Dashboard | Streamlit |
| Backend API | FastAPI |
| AI Workflow | LangGraph |
| LLM Gateway | OpenRouter |
| Database | SQLite (dev) / PostgreSQL (production) |
| ORM | SQLAlchemy |
| Scheduling | APScheduler |
| Publishing | WordPress REST API |

---

## 5. Project Structure (Quick Reference)

```
ai-content-system/
├── app/                    # Entry point and configuration
├── api/                    # FastAPI routes
├── agents/                 # LangGraph agents (nodes)
├── graphs/                 # Graph and workflow definition
├── services/               # OpenRouter, WordPress, Token Tracker
├── scheduler/              # Scheduling tasks
├── dashboard/              # Streamlit application
├── models/                 # Data models (Pydantic/SQLAlchemy)
└── docs/                   # Documentation
```

Full file layout is in [Phases and Roadmap](../development/phases-and-roadmap.md).
