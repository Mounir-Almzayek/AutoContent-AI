# AutoContent AI

AI-powered content generation, review, and publishing to WordPress.

## Introduction

AutoContent AI is an integrated system that manages keywords, runs an AI content pipeline (keyword analysis → brief → article → quality check → duplicate check → SEO optimization), stores articles in a database, schedules generation and publishing, and publishes to WordPress via the REST API. You manage keywords, scheduling, and settings and monitor token usage through a Streamlit dashboard that talks to a FastAPI backend.

## Screenshots

| Dashboard — Articles | Keywords & trend discovery |
|---------------------|-----------------------------|
| ![Articles](docs/screenshot/Screenshot%202026-03-12%20151520.png) | ![Keywords](docs/screenshot/Screenshot%202026-03-12%20145515.png) |

| Token usage | AI Settings | Content calendar |
|-------------|-------------|-------------------|
| ![Article preview](docs/screenshot/Screenshot%202026-03-12%20151548.png) | ![Settings](docs/screenshot/Screenshot%202026-03-12%20153157.png) | ![Calendar](docs/screenshot/Screenshot%202026-03-12%20151726.png) |

## Tech stack

- **Dashboard:** Streamlit  
- **Backend:** FastAPI  
- **AI workflow:** LangGraph, OpenRouter (LLM)  
- **Database:** SQLite (dev) / PostgreSQL (production)  
- **Scheduling:** APScheduler  
- **Publishing:** WordPress REST API  

## Project structure

```
├── app/           # Entry point, config, database
├── api/           # FastAPI routes
├── agents/        # AI agents (keyword, brief, article, quality, duplicate, seo, trend)
├── graphs/        # LangGraph workflow
├── services/      # OpenRouter, WordPress, token tracker
├── scheduler/     # APScheduler jobs and rules
├── dashboard/     # Streamlit app
├── models/        # Data models
└── docs/          # Documentation
```

## Getting started

### 1. Environment

Copy `.env.example` to `.env` and set:

- `OPENROUTER_API_KEY` — required for AI generation  
- `BACKEND_URL` — e.g. `http://localhost:8000` (for the dashboard)  
- Optional: `WORDPRESS_*` for publishing to WordPress  

### 2. Install and run (local)

```bash
pip install -r requirements.txt
```

**Terminal 1 — Backend:**

```bash
uvicorn app.main:app --reload
```

**Terminal 2 — Dashboard:**

```bash
streamlit run dashboard/streamlit_app.py
```

- API: http://localhost:8000 (docs: http://localhost:8000/docs)  
- Dashboard: http://localhost:8501  

### 3. Run with Docker

Create `.env` from `.env.example` first, then:

```bash
docker-compose up --build
```

- Dashboard: http://localhost:8501  
- API: http://localhost:8000  

Containers and volumes use unique names (`autocontent_ai_backend`, `autocontent_ai_dashboard`, `autocontent_ai_backend_data`) to avoid conflicts with other deployments.

### 4. Deployment behind nginx (two domains)

If you expose the app via nginx (no direct port access), use **one domain for the API** and **one for the Dashboard**. Example config: **[nginx/autocontent-ai.conf.example](nginx/autocontent-ai.conf.example)**. See [nginx/README.md](nginx/README.md) for setup steps.

## Documentation

Full technical documentation (architecture, API, dashboard, data models, integrations) is in **[docs/README.md](docs/README.md)**.
