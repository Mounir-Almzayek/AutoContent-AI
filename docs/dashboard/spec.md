# Dashboard Specification (Streamlit)

## 1. Overview

- Single app: `dashboard/streamlit_app.py`.
- Sidebar navigation between pages.
- Communicates with the backend via `httpx` to the FastAPI base URL (e.g. `http://localhost:8000`), configured by `BACKEND_URL` (env or default).

---

## 2. Pages

### Page 1 — Articles

| Element | Description |
|---------|-------------|
| Table | List from GET `/articles` with title, status, date, keyword |
| Filter | Filter by status (draft, generating, ready, published, failed) |
| Generate | Form: select keyword, language, tone, then POST `/articles/generate` |
| Select article | Dropdown to view/edit or publish a single article |
| Publish | Button to call POST `/articles/{id}/publish` |

### Page 2 — Keywords Manager

| Element | Description |
|---------|-------------|
| Table | List from GET `/keywords` with search and filter by status |
| Add keyword | Form to add one or multiple keywords |
| Import | File upload (csv/txt) and POST `/keywords/import` |
| Edit/Delete | Actions per row |
| Trend discovery | Form: niche, language, time window; POST `/keywords/trend-discovery`; then option to import selected results via POST `/keywords/import-from-trends` |

### Page 3 — Token Usage

| Element | Description |
|---------|-------------|
| Period | Radio: day / week / month |
| Data | GET `/usage/tokens` and optionally `/usage/by-article` |
| Display | Summary and/or chart of token consumption and cost |

### Page 4 — AI Settings

| Element | Description |
|---------|-------------|
| Per-agent settings | Model, temperature, max tokens (from GET `/settings/ai`) |
| Save | PATCH `/settings/ai` to update settings |

### Page 5 — Content Calendar

| Element | Description |
|---------|-------------|
| Calendar view | Scheduled items from GET `/scheduler/calendar` and/or jobs/articles |
| Schedule article | Pick article and time; POST `/scheduler/schedule-article` |
| Schedule generation | Pick keyword and time; POST `/scheduler/schedule-generation` |
| Recurring rules | List from GET `/scheduler/rules`; create/edit/pause/resume/delete rules (POST/PATCH/DELETE `/scheduler/rules`, pause/resume endpoints) |
| Jobs list | List from GET `/scheduler/jobs`; cancel via DELETE `/scheduler/jobs/{job_id}` |

---

## 3. Shared Behavior

- **Backend URL:** From env `BACKEND_URL` or default in code.
- **Errors:** Show API error messages in the UI (e.g. `st.error`).
- **Refresh:** Re-run queries when filters or period change (Streamlit rerun).

---

## 4. Recommended Implementation Order

1. Sidebar with page buttons.
2. Articles page (core).
3. Keywords Manager (including trend discovery).
4. AI Settings.
5. Token Usage.
6. Content Calendar (depends on scheduler and rules API).

---

## 5. Screenshots

Screenshots of the dashboard are in [../screenshot/](../screenshot/). Use them in the root README and here for visual reference (e.g. Articles view, Keywords and trend discovery, Token usage, AI Settings, Content calendar).
