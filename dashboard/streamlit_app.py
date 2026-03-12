"""
Streamlit Dashboard: Content Calendar, Keywords, Articles, Token Usage, AI Settings.
See docs/dashboard/spec.md. Connects to FastAPI backend at BACKEND_URL.
"""
import os
from datetime import datetime, timezone, timedelta

import pandas as pd
import httpx
import streamlit as st

# Backend base URL (no trailing slash)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
API_BASE = f"{BACKEND_URL}/api/v1"

# Status pills (label, color hex)
STATUS_CONFIG = {
    "draft": ("Draft", "#6b7280"),
    "generating": ("Generating", "#f59e0b"),
    "ready": ("Ready", "#10b981"),
    "published": ("Published", "#3b82f6"),
    "failed": ("Failed", "#ef4444"),
    "pending": ("Pending", "#6b7280"),
    "processed": ("Processed", "#10b981"),
}


def status_badge(status: str) -> str:
    label, color = STATUS_CONFIG.get(status, (status or "—", "#6b7280"))
    return f'<span style="display:inline-block;padding:0.2em 0.5em;border-radius:999px;font-size:0.75rem;font-weight:600;background:{color}20;color:{color};">{label}</span>'


def format_short_date(s: str | None) -> str:
    if not s:
        return "—"
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return str(s)[:19]

# Example free OpenRouter model IDs (user types any model ID manually)
OPENROUTER_FREE_EXAMPLES = [
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2-7b-instruct:free",
]


def api_get(path: str, params: dict | None = None) -> tuple[dict | list | None, str | None]:
    """GET request to API. Returns (data, error_message)."""
    url = f"{API_BASE}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, params=params or {})
            r.raise_for_status()
            return r.json(), None
    except httpx.HTTPStatusError as e:
        return None, f"API {e.response.status_code}: {e.response.text[:500]}"
    except Exception as e:
        return None, str(e)


def api_post(path: str, json: dict | None = None, files: dict | None = None) -> tuple[dict | None, str | None]:
    """POST request. Returns (data, error_message). Long timeout for trend discovery / generation."""
    url = f"{API_BASE}{path}"
    try:
        with httpx.Client(timeout=300.0) as client:
            if files:
                r = client.post(url, files=files)
            else:
                r = client.post(url, json=json or {})
            r.raise_for_status()
            return r.json() if r.content else {}, None
    except httpx.HTTPStatusError as e:
        return None, f"API {e.response.status_code}: {e.response.text[:500]}"
    except Exception as e:
        return None, str(e)


def api_patch(path: str, json: dict) -> tuple[dict | None, str | None]:
    """PATCH request. Returns (data, error_message)."""
    url = f"{API_BASE}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.patch(url, json=json)
            r.raise_for_status()
            return r.json(), None
    except httpx.HTTPStatusError as e:
        return None, f"API {e.response.status_code}: {e.response.text[:500]}"
    except Exception as e:
        return None, str(e)


def api_delete(path: str) -> tuple[bool, str | None]:
    """DELETE request. Returns (success, error_message)."""
    url = f"{API_BASE}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.delete(url)
            r.raise_for_status()
            return True, None
    except httpx.HTTPStatusError as e:
        return False, f"API {e.response.status_code}: {e.response.text[:500]}"
    except Exception as e:
        return False, str(e)


def page_articles():
    st.title("Articles Manager")
    tab_list, tab_generate = st.tabs(["Article list", "Generate new article"])
    with tab_list:
        search_art = st.text_input("Search by title", key="art_search", placeholder="Type to filter by article title…")
        status_filter = st.selectbox("Filter by status", ["", "draft", "generating", "ready", "published", "failed"], key="art_status")
        params = {"limit": 100}
        if status_filter:
            params["status"] = status_filter
        if search_art and search_art.strip():
            params["q"] = search_art.strip()
        with st.spinner("Loading articles…"):
            data, err = api_get("/articles", params=params)
        if err:
            st.error(err)
            st.caption("Check that the backend is running and try again.")
            return
        items = data.get("items") or []
        total = data.get("total") or 0
        by_status = {}
        for a in items:
            s = a.get("status") or "draft"
            by_status[s] = by_status.get(s, 0) + 1
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total", total)
        m2.metric("Draft", by_status.get("draft", 0))
        m3.metric("Ready", by_status.get("ready", 0))
        m4.metric("Published", by_status.get("published", 0))
        m5.metric("Failed", by_status.get("failed", 0))

        # Article preview (full-screen readable)
        if st.session_state.get("preview_article"):
            art = st.session_state["preview_article"]
            st.divider()
            with st.container():
                st.markdown("---")
                st.subheader("📄 Article preview")
                st.markdown(f"**{art.get('title') or 'Untitled'}**")
                st.caption(f"ID {art.get('id')} · {art.get('status', '')} · {format_short_date(art.get('created_at'))}")
                if art.get("meta_description"):
                    st.caption(art.get("meta_description"))
                st.markdown("---")
                content = (art.get("content") or "").strip()
                if content:
                    st.markdown(content, unsafe_allow_html=True)
                else:
                    st.info("No content.")
                st.markdown("---")
                if st.button("Close preview", key="close_preview"):
                    del st.session_state["preview_article"]
                    if "preview_article_id" in st.session_state:
                        del st.session_state["preview_article_id"]
                    st.rerun()
            st.divider()

        filtered = items
        if not filtered:
            st.info("No articles yet. Use the **Generate new article** tab to create one.")
        else:
            df = pd.DataFrame([
                {
                    "ID": a.get("id"),
                    "Title": (a.get("title") or "Untitled")[:80],
                    "Status": (a.get("status") or "draft").capitalize(),
                    "Created": format_short_date(a.get("created_at")),
                    "Meta": (a.get("meta_title") or "")[:40] or "—",
                }
                for a in filtered
            ])
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "Title": st.column_config.TextColumn("Title", width="large"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Created": st.column_config.TextColumn("Created", width="medium"),
                    "Meta": st.column_config.TextColumn("Meta title", width="medium"),
                },
            )
            st.caption("Use the actions below for the selected article.")
            sel_col, btn_col = st.columns([2, 3])
            with sel_col:
                options = {f"#{a['id']} — {(a.get('title') or 'Untitled')[:50]}": a["id"] for a in filtered}
                selected_label = st.selectbox("Select article", options=list(options.keys()), key="art_sel", label_visibility="collapsed")
                selected_id = options.get(selected_label) if selected_label else None
            with btn_col:
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    if st.button("Preview", key="art_btn_preview", disabled=not selected_id):
                        det, e = api_get(f"/articles/{selected_id}")
                        if e:
                            st.error(e)
                        else:
                            st.session_state["preview_article"] = det
                            st.session_state["preview_article_id"] = selected_id
                            st.rerun()
                with b2:
                    art_status = next((a.get("status") for a in filtered if a["id"] == selected_id), "")
                    if st.button("Publish", key="art_btn_pub", disabled=not selected_id or art_status != "ready"):
                        _, e = api_post(f"/articles/{selected_id}/publish")
                        if e:
                            st.error(e)
                        else:
                            st.success("Published")
                            st.rerun()
                with b3:
                    if st.button("View JSON", key="art_btn_json", disabled=not selected_id):
                        det, e = api_get(f"/articles/{selected_id}")
                        if e:
                            st.error(e)
                        else:
                            st.json(det)
                with b4:
                    if st.button("Delete", key="art_btn_del", disabled=not selected_id, type="secondary"):
                        ok, e = api_delete(f"/articles/{selected_id}")
                        if e:
                            st.error(e)
                        else:
                            st.success("Deleted")
                            st.rerun()
    with tab_generate:
        with st.form("generate_form"):
            keyword = st.text_input("Keyword", placeholder="e.g. best SEO tools 2024", help="Main topic for the article.")
            with st.expander("Options", expanded=False):
                lang = st.text_input("Language", value="en")
                tone = st.selectbox("Tone", ["professional", "friendly", "technical", "conversational"])
                wc = st.number_input("Word count target", min_value=500, max_value=10000, value=1500)
            if st.form_submit_button("Generate article"):
                if not keyword.strip():
                    st.error("Enter a keyword.")
                else:
                    payload = {"keyword": keyword.strip(), "options": {"language": lang, "tone": tone, "word_count_target": wc}}
                    with st.spinner("Generating article… This may take 1–2 minutes."):
                        out, e = api_post("/articles/generate", json=payload)
                    if e:
                        st.error(e)
                    else:
                        if out.get("status") == "success" and out.get("article_id"):
                            st.success(f"Article created (ID {out['article_id']}). Check the Article list tab.")
                        else:
                            st.warning(out.get("error", out.get("status", "Unknown")))
                        st.rerun()


def page_keywords():
    st.title("Keywords Manager")
    tab_list, tab_add, tab_import, tab_trends = st.tabs(["Keyword list", "Add keyword", "Import from file", "Discover trends"])
    with tab_list:
        search_kw = st.text_input("Search by name", key="kw_search", placeholder="Type to filter by keyword…")
        status_f = st.selectbox("Filter by status", ["", "pending", "processed", "failed"], key="kw_status")
        params = {"limit": 100}
        if status_f:
            params["status"] = status_f
        if search_kw and search_kw.strip():
            params["q"] = search_kw.strip()
        with st.spinner("Loading keywords…"):
            data, err = api_get("/keywords", params=params)
        if err:
            st.error(err)
            return
        items = data.get("items") or []
        total = data.get("total") or 0
        st.metric("Total keywords", total)
        filtered = items
        if not filtered:
            st.info("No keywords yet. Use **Add keyword** or **Import from file** to add some.")
        else:
            df = pd.DataFrame([
                {
                    "ID": k.get("id"),
                    "Keyword": (k.get("keyword") or "")[:100],
                    "Topic": (k.get("topic") or "—")[:60],
                    "Intent": (k.get("search_intent") or "—")[:20],
                    "Status": (k.get("status") or "pending").capitalize(),
                }
                for k in filtered
            ])
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "Keyword": st.column_config.TextColumn("Keyword", width="large"),
                    "Topic": st.column_config.TextColumn("Topic", width="medium"),
                    "Intent": st.column_config.TextColumn("Intent", width="small"),
                    "Status": st.column_config.TextColumn("Status", width="small"),
                },
            )
            st.caption("Select a keyword below to delete it.")
            sel_col, btn_col = st.columns([2, 1])
            with sel_col:
                options = {f"#{k['id']} — {(k.get('keyword') or '')[:60]}": k["id"] for k in filtered}
                selected_label = st.selectbox("Select keyword", options=list(options.keys()), key="kw_sel", label_visibility="collapsed")
                selected_id = options.get(selected_label) if selected_label else None
            with btn_col:
                if st.button("Delete selected", key="kw_btn_del", disabled=not selected_id, type="secondary"):
                    ok, e = api_delete(f"/keywords/{selected_id}")
                    if e:
                        st.error(e)
                    else:
                        st.success("Deleted")
                        st.rerun()
    with tab_add:
        with st.form("add_keyword"):
            kw = st.text_input("Keyword", key="new_kw", placeholder="e.g. best CRM software 2024")
            if st.form_submit_button("Add keyword"):
                if not kw.strip():
                    st.error("Enter a keyword.")
                else:
                    out, e = api_post("/keywords", json={"keyword": kw.strip()})
                    if e:
                        st.error(e)
                    else:
                        st.success("Keyword added.")
                        st.rerun()
    with tab_import:
        uploaded = st.file_uploader("Upload CSV or TXT", type=["csv", "txt"], key="kw_upload", help="One keyword per line or comma-separated. Lines starting with # are ignored.")
        if uploaded and st.button("Import keywords"):
            with st.spinner("Importing…"):
                out, e = api_post("/keywords/import", files={"file": (uploaded.name, uploaded.getvalue())})
            if e:
                st.error(e)
            else:
                imp = out.get("imported", 0)
                st.success(f"Imported {imp} new keyword(s). {out.get('total_unique', 0)} unique in file.")
                st.rerun()

    with tab_trends:
        st.caption("Discover trending topics and SEO keywords for your niche. Results can be added to your keyword list for content generation.")
        with st.form("trend_discovery"):
            niche = st.text_input("Niche / industry", value="AI tools", placeholder="e.g. digital marketing, fintech, SaaS", key="trend_niche")
            lang_trend = st.text_input("Language", value="en", max_chars=16, key="trend_lang")
            num_kw = st.number_input("Number of keywords", min_value=1, max_value=20, value=5, key="trend_num")
            time_window = st.selectbox(
                "Time window for trends",
                ["last week", "last month", "current trends"],
                key="trend_window",
            )
            if st.form_submit_button("Discover trends"):
                if not niche or not niche.strip():
                    st.error("Enter a niche or industry.")
                else:
                    with st.spinner("Discovering trends (this may take a moment)…"):
                        out, e = api_post(
                            "/keywords/trend-discovery",
                            json={
                                "niche": niche.strip(),
                                "language": lang_trend,
                                "number_of_keywords": num_kw,
                                "time_window": time_window,
                            },
                        )
                    if e:
                        st.error(e)
                    else:
                        st.session_state["trend_results"] = out.get("items") or []
                        st.session_state["trend_done"] = True
                        st.rerun()

        if st.session_state.get("trend_done") and st.session_state.get("trend_results"):
            results = st.session_state["trend_results"]
            st.subheader(f"Results ({len(results)} items)")
            st.divider()
            df_trend = pd.DataFrame([
                {
                    "#": i + 1,
                    "Trend": (r.get("trend_topic") or "")[:50],
                    "Primary keyword": (r.get("primary_keyword") or "")[:50],
                    "Intent": (r.get("search_intent") or "Informational")[:20],
                    "Words": r.get("recommended_word_count", 1500),
                    "Article title": (r.get("article_title") or "")[:60],
                }
                for i, r in enumerate(results)
            ])
            st.dataframe(
                df_trend,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "#": st.column_config.NumberColumn("#", width="small"),
                    "Trend": st.column_config.TextColumn("Trend", width="medium"),
                    "Primary keyword": st.column_config.TextColumn("Primary keyword", width="medium"),
                    "Intent": st.column_config.TextColumn("Intent", width="small"),
                    "Words": st.column_config.NumberColumn("Words", width="small"),
                    "Article title": st.column_config.TextColumn("Article title", width="large"),
                },
            )
            st.caption("Select an item to add, or add all. Use buttons above to add all or clear.")
            sel_col, b1, b2, b3 = st.columns([2, 1, 1, 1])
            with sel_col:
                options_trend = {f"#{i+1} — {r.get('primary_keyword', '')[:45]}": i for i, r in enumerate(results)}
                selected_label_t = st.selectbox("Select result", options=list(options_trend.keys()), key="trend_sel", label_visibility="collapsed")
                selected_idx = options_trend.get(selected_label_t) if selected_label_t else None
            with b1:
                if st.button("Add selected", key="trend_add_sel", disabled=selected_idx is None):
                    payload = {"items": [results[selected_idx]]}
                    out_imp, err = api_post("/keywords/import-from-trends", json=payload)
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Added {out_imp.get('imported', 0)} keyword(s).")
                        st.rerun()
            with b2:
                if st.button("Add all", key="trend_add_all_btn"):
                    payload = {"items": results}
                    out_imp, err = api_post("/keywords/import-from-trends", json=payload)
                    if err:
                        st.error(err)
                    else:
                        st.success(f"Added {out_imp.get('imported', 0)} keyword(s).")
                        st.session_state["trend_results"] = []
                        st.session_state["trend_done"] = False
                        st.rerun()
            with b3:
                if st.button("Clear results", key="trend_clear_btn"):
                    st.session_state["trend_results"] = []
                    st.session_state["trend_done"] = False
                    st.rerun()


def page_usage():
    st.title("Token Usage")
    period = st.radio("Period", ["day", "week", "month"], key="usage_period", horizontal=True)
    with st.spinner("Loading…"):
        data, err = api_get("/usage/tokens", params={"period": period})
    if err:
        st.error(err)
        return
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total tokens", f"{data.get('total_tokens', 0):,}")
    c2.metric("Prompt", f"{data.get('total_prompt_tokens', 0):,}")
    c3.metric("Completion", f"{data.get('total_completion_tokens', 0):,}")
    cost = data.get("total_cost")
    c4.metric("Total cost", f"{cost:.4f}" if cost is not None else "—")
    c5.metric("API calls", data.get("record_count", 0))
    st.caption(f"From {format_short_date(data.get('period_start'))} to {format_short_date(data.get('period_end'))}")


# Agent IDs for per-agent model settings (must match backend AGENT_IDS)
AI_AGENT_LABELS = [
    ("default", "Default (fallback for all agents)"),
    ("keyword_agent", "Keyword analyzer"),
    ("brief_agent", "Content brief"),
    ("article_agent", "Article generator"),
    ("quality_agent", "Quality check"),
    ("duplicate_agent", "Duplicate check"),
    ("seo_agent", "SEO optimizer"),
    ("trend_agent", "Trend discovery"),
]


def page_settings():
    st.title("AI Settings")
    st.caption("Set a model per agent. Empty = use Default. Each agent will use the model you set here.")
    with st.spinner("Loading…"):
        data, err = api_get("/settings/ai")
    if err:
        st.error(err)
        return
    default = data.get("default") or {}
    agents = data.get("agents") or {}
    with st.container():
        with st.form("ai_settings"):
            st.subheader("Per-agent model (OpenRouter model ID)")
            with st.expander("Free models (OpenRouter)", expanded=False):
                st.caption("Full list: [openrouter.ai/models](https://openrouter.ai/models)")
                for ex in OPENROUTER_FREE_EXAMPLES:
                    st.code(ex, language=None)
            inputs = {}
            for agent_id, label in AI_AGENT_LABELS:
                if agent_id == "default":
                    row = default
                    val = (row.get("model") or "openai/gpt-4o").strip()
                    inputs["default_model"] = st.text_input("Default — model", value=val, placeholder="e.g. openai/gpt-4o", key="set_default_model")
                    c1, c2 = st.columns(2)
                    with c1:
                        inputs["default_temp"] = st.slider("Default — temperature", 0.0, 2.0, float(default.get("temperature", 0.7)), 0.1, key="set_default_temp")
                    with c2:
                        inputs["default_max_tok"] = st.number_input("Default — max tokens", min_value=256, max_value=128000, value=int(default.get("max_tokens", 4096)), key="set_default_maxtok")
                else:
                    row = agents.get(agent_id) or {}
                    val = (row.get("model") or "").strip()
                    inputs[agent_id] = st.text_input(f"{label} — model (empty = use Default)", value=val, placeholder="empty = Default", key=f"set_{agent_id}")
            if st.form_submit_button("Save settings"):
                payload = {
                    "default": {
                        "model": (inputs.get("default_model") or "").strip() or "openai/gpt-4o",
                        "temperature": inputs.get("default_temp", 0.7),
                        "max_tokens": inputs.get("default_max_tok", 4096),
                    },
                    "agents": {},
                }
                for agent_id, _ in AI_AGENT_LABELS:
                    if agent_id == "default":
                        continue
                    payload["agents"][agent_id] = {"model": (inputs.get(agent_id) or "").strip()}
                out, e = api_patch("/settings/ai", json=payload)
                if e:
                    st.error(e)
                else:
                    st.success("Settings saved. Each agent will use its assigned model.")
                    st.rerun()


def _calendar_events_by_date(events: list) -> dict:
    """Group calendar events by date (YYYY-MM-DD)."""
    by_date = {}
    for e in events:
        run_at = e.get("run_at") or ""
        date_key = run_at[:10] if len(run_at) >= 10 else "unknown"
        by_date.setdefault(date_key, []).append(e)
    for k in by_date:
        by_date[k].sort(key=lambda x: x.get("run_at") or "")
    return by_date


def _format_interval_minutes(m: int | None) -> str:
    """e.g. 360 -> 'Every 6h', 30 -> 'Every 30 min'."""
    if m is None or m <= 0:
        return "—"
    if m >= 60 and m % 60 == 0:
        h = m // 60
        return f"Every {h}h" if h < 24 else f"Every {h // 24}d"
    return f"Every {m} min"


def _format_publish_behavior(behavior: str, delay_min: int | None) -> str:
    """Human-readable publish behavior."""
    if behavior == "draft":
        return "Draft only"
    if behavior == "immediate":
        return "Publish immediately"
    if behavior == "delay":
        return f"Publish after {delay_min or 0} min"
    return behavior or "—"


def page_calendar():
    st.title("Content Calendar")
    with st.spinner("Loading…"):
        jobs_data, err_j = api_get("/scheduler/jobs")
        stats, _ = api_get("/scheduler/stats")
        rules_data, err_r = api_get("/scheduler/rules")
    if err_j:
        st.error(err_j)
        return
    jobs = jobs_data.get("jobs") or []
    rules = rules_data if isinstance(rules_data, list) else (rules_data.get("rules") or []) if isinstance(rules_data, dict) else []
    if err_r:
        rules = []

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Scheduled jobs", stats.get("total_jobs", 0))
    with m2:
        next_run = stats.get("next_run")
        st.metric("Next run", format_short_date(next_run) if next_run else "—")
    with m3:
        active_rules = sum(1 for r in rules if r.get("enabled"))
        st.metric("Active rules", f"{active_rules} / {len(rules)}")
    with m4:
        total_gen = sum((r.get("last_articles_count") or 0) for r in rules)
        st.metric("Last run articles", total_gen)

    tab_cal, tab_onetime, tab_recurring, tab_jobs, tab_system = st.tabs([
        "Calendar view", "One-time schedule", "Recurring rules", "Job management", "System",
    ])

    with tab_cal:
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=31)
        cal, err_c = api_get("/scheduler/calendar", params={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        })
        if err_c:
            st.warning("Calendar API: " + err_c)
        else:
            events = (cal or {}).get("events") or []
            if not events:
                st.info("No events in the next 31 days. Schedule jobs or recurring rules to see them here.")
            else:
                rows = []
                for e in events:
                    run_at = e.get("run_at") or ""
                    date_key = run_at[:10] if len(run_at) >= 10 else "—"
                    typ = e.get("type", "job")
                    if typ == "article":
                        rows.append({"Date": date_key, "Type": "Article", "Target": e.get("title") or f"ID {e.get('id')}", "Run at": run_at[:19] if run_at else "—"})
                    else:
                        rid = e.get("article_id") or e.get("keyword_id") or e.get("rule_id")
                        rows.append({"Date": date_key, "Type": e.get("job_type", "job"), "Target": f"ID {rid}", "Run at": run_at[:19] if run_at else "—"})
                df_cal = pd.DataFrame(rows)
                df_cal = df_cal.sort_values(by=["Date", "Run at"], ascending=[True, True])
                st.dataframe(
                    df_cal,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Date": st.column_config.TextColumn("Date", width="small"),
                        "Type": st.column_config.TextColumn("Type", width="small"),
                        "Target": st.column_config.TextColumn("Target", width="large"),
                        "Run at": st.column_config.TextColumn("Run at", width="medium"),
                    },
                )

    with tab_onetime:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Schedule article publish")
            arts, _ = api_get("/articles", params={"status": "ready", "limit": 50})
            art_list = (arts or {}).get("items") or []
            if not art_list:
                st.caption("No articles with status **ready** to schedule.")
            with st.form("sched_article"):
                art_id = st.selectbox("Article", [a["id"] for a in art_list], format_func=lambda x: next((f"ID {a['id']}: {a.get('title','')[:40]}" for a in art_list if a["id"] == x), str(x))) if art_list else None
                run_at = st.datetime_input("Publish at", value=datetime.now(timezone.utc) + timedelta(hours=1))
                if st.form_submit_button("Schedule publish") and art_id:
                    out, e = api_post("/scheduler/schedule-article", json={"article_id": art_id, "scheduled_at": run_at.isoformat()})
                    if e:
                        st.error(e)
                    else:
                        st.toast("Publish scheduled.")
                        st.rerun()
        with col_b:
            st.subheader("Schedule generation")
            kw_data, _ = api_get("/keywords", params={"limit": 100})
            kw_list = (kw_data or {}).get("items") or []
            if not kw_list:
                st.caption("No keywords. Add keywords first.")
            with st.form("sched_gen"):
                kw_id = st.selectbox("Keyword", [k["id"] for k in kw_list], format_func=lambda x: next((f"ID {k['id']}: {k.get('keyword','')}" for k in kw_list if k["id"] == x), str(x))) if kw_list else None
                run_at_g = st.datetime_input("Run at", value=datetime.now(timezone.utc) + timedelta(hours=2), key="run_at_gen")
                if st.form_submit_button("Schedule generation") and kw_id:
                    out, e = api_post("/scheduler/schedule-generation", json={"keyword_id": kw_id, "scheduled_at": run_at_g.isoformat()})
                    if e:
                        st.error(e)
                    else:
                        st.toast("Generation scheduled.")
                        st.rerun()

    with tab_recurring:
        keyword_rules = [r for r in rules if r.get("rule_type") == "keywords"]
        article_rules = [r for r in rules if r.get("rule_type") != "keywords"]

        st.subheader("🔑 Keyword scheduler")
        st.caption("Run trend discovery every X minutes and add new keywords to the list.")
        if keyword_rules:
            df_kw_rules = pd.DataFrame([
                {
                    "ID": r.get("id"),
                    "Name": (r.get("name") or "")[:40],
                    "Interval": _format_interval_minutes(r.get("interval_minutes")),
                    "Niche": (r.get("niche") or "—")[:35],
                    "Kw/run": r.get("trend_keywords_count") or 5,
                    "Last run": format_short_date(r.get("last_run_at")),
                    "Added": r.get("last_keywords_count") or 0,
                    "Status": "🟢 Active" if r.get("enabled", True) else "⏸ Paused",
                }
                for r in keyword_rules
            ])
            st.dataframe(df_kw_rules, use_container_width=True, hide_index=True)
            st.caption("Select a rule to pause, resume, delete, or edit.")
            ksel, kbtn1, kbtn2 = st.columns([2, 1, 1])
            with ksel:
                kw_opts = {f"#{r['id']} {r.get('name','')[:35]}": r["id"] for r in keyword_rules}
                kw_sel_label = st.selectbox("Rule", list(kw_opts.keys()), key="kw_rule_sel", label_visibility="collapsed")
                kw_rid = kw_opts.get(kw_sel_label) if kw_sel_label else None
            r_kw = next((r for r in keyword_rules if r["id"] == kw_rid), None) if kw_rid else None
            with kbtn1:
                if r_kw and st.button("Pause" if r_kw.get("enabled", True) else "Resume", key="kw_toggle"):
                    path = f"/scheduler/rules/{kw_rid}/pause" if r_kw.get("enabled", True) else f"/scheduler/rules/{kw_rid}/resume"
                    _, e = api_post(path)
                    if e:
                        st.error(e)
                    else:
                        st.toast("Rule updated.")
                        st.rerun()
            with kbtn2:
                if st.button("Delete", key="kw_del_btn", disabled=not kw_rid):
                    api_delete(f"/scheduler/rules/{kw_rid}")
                    st.toast("Rule deleted.")
                    st.rerun()
            with st.expander("Edit selected rule", expanded=False):
                if r_kw:
                    with st.form("edit_kw_rule_form"):
                        e_name = st.text_input("Name", value=r_kw.get("name", ""), max_chars=256, key="ekw_name")
                        e_interval = st.number_input("Interval (min)", min_value=1, max_value=525600, value=r_kw.get("interval_minutes") or 360, key="ekw_interval")
                        e_niche = st.text_input("Niche", value=r_kw.get("niche") or "", max_chars=256, key="ekw_niche")
                        e_trend_n = st.number_input("Keywords per run", min_value=1, max_value=20, value=r_kw.get("trend_keywords_count") or 5, key="ekw_n")
                        e_time_window = st.selectbox("Time window", ["last week", "last month", "current trends"], index=["last week", "last month", "current trends"].index(r_kw.get("trend_time_window") or "last month"), key="ekw_tw")
                        e_lang = st.text_input("Language", value=r_kw.get("language", "en"), max_chars=16, key="ekw_lang")
                        if st.form_submit_button("Save"):
                            _, err = api_patch(f"/scheduler/rules/{kw_rid}", json={"name": e_name, "trigger_type": "interval", "interval_minutes": e_interval, "niche": e_niche.strip() or None, "trend_keywords_count": e_trend_n, "trend_time_window": e_time_window, "language": e_lang})
                            if err:
                                st.error(err)
                            else:
                                st.toast("Rule updated.")
                                st.rerun()
        else:
            st.info("No keyword rules. Add one below.")
        with st.expander("➕ Add keyword rule", expanded=(len(keyword_rules) == 0)):
            with st.form("add_kw_rule"):
                name = st.text_input("Rule name", value="Trend discovery", max_chars=256, key="add_kw_name")
                interval_minutes = st.number_input("Interval (minutes)", min_value=1, max_value=525600, value=360, key="add_kw_interval")
                niche = st.text_input("Niche", value="AI tools", placeholder="e.g. digital marketing", max_chars=256, key="add_kw_niche")
                trend_keywords_count = st.number_input("Keywords per run", min_value=1, max_value=20, value=5, key="add_kw_count")
                trend_time_window = st.selectbox("Time window", ["last week", "last month", "current trends"], key="add_kw_tw")
                language = st.text_input("Language", value="en", max_chars=16, key="add_kw_lang")
                if st.form_submit_button("Create keyword rule"):
                    if not niche.strip():
                        st.error("Enter a niche.")
                    else:
                        payload = {"rule_type": "keywords", "name": name, "trigger_type": "interval", "interval_minutes": interval_minutes, "niche": niche.strip(), "trend_keywords_count": trend_keywords_count, "trend_time_window": trend_time_window, "language": language, "enabled": True}
                        out, e = api_post("/scheduler/rules", json=payload)
                        if e:
                            st.error(e)
                        else:
                            st.toast("Keyword rule created.")
                            st.rerun()

        st.subheader("📄 Article scheduler")
        st.caption("Generate articles from all pending keywords every X minutes and publish immediately.")
        if article_rules:
            df_art_rules = pd.DataFrame([
                {
                    "ID": r.get("id"),
                    "Name": (r.get("name") or "")[:40],
                    "Interval": _format_interval_minutes(r.get("interval_minutes")),
                    "Art/run": r.get("articles_per_run", 1),
                    "Last run": format_short_date(r.get("last_run_at")),
                    "Generated": r.get("last_articles_count") or 0,
                    "Status": "🟢 Active" if r.get("enabled", True) else "⏸ Paused",
                }
                for r in article_rules
            ])
            st.dataframe(df_art_rules, use_container_width=True, hide_index=True)
            st.caption("Select a rule to pause, resume, delete, or edit.")
            asel, abtn1, abtn2, aedit = st.columns([2, 1, 1, 1])
            with asel:
                art_opts = {f"#{r['id']} {r.get('name','')[:35]}": r["id"] for r in article_rules}
                art_sel_label = st.selectbox("Rule", list(art_opts.keys()), key="art_rule_sel", label_visibility="collapsed")
                art_rid = art_opts.get(art_sel_label) if art_sel_label else None
            r_art = next((r for r in article_rules if r["id"] == art_rid), None) if art_rid else None
            with abtn1:
                if r_art and st.button("Pause" if r_art.get("enabled", True) else "Resume", key="art_toggle"):
                    path = f"/scheduler/rules/{art_rid}/pause" if r_art.get("enabled", True) else f"/scheduler/rules/{art_rid}/resume"
                    _, e = api_post(path)
                    if e:
                        st.error(e)
                    else:
                        st.toast("Rule updated.")
                        st.rerun()
            with abtn2:
                if st.button("Delete", key="art_del_btn", disabled=not art_rid):
                    api_delete(f"/scheduler/rules/{art_rid}")
                    st.toast("Rule deleted.")
                    st.rerun()
            with st.expander("Edit selected rule", expanded=False):
                if r_art:
                    with st.form("edit_art_rule_form"):
                        e_name = st.text_input("Name", value=r_art.get("name", ""), max_chars=256, key="art_name_edit")
                        e_interval = st.number_input("Interval (min)", min_value=1, max_value=525600, value=r_art.get("interval_minutes") or 360, key="art_interval_edit")
                        e_articles = st.number_input("Articles per run", min_value=1, max_value=20, value=r_art.get("articles_per_run", 1), key="art_n_edit")
                        e_lang = st.text_input("Language", value=r_art.get("language", "en"), max_chars=16, key="art_lang_edit")
                        e_tone = st.text_input("Tone", value=r_art.get("tone", "professional"), max_chars=32, key="art_tone_edit")
                        e_words = st.number_input("Word count target", min_value=300, max_value=20000, value=r_art.get("word_count_target", 1500), key="art_words_edit")
                        if st.form_submit_button("Save"):
                            payload = {"name": e_name, "trigger_type": "interval", "interval_minutes": e_interval, "articles_per_run": e_articles, "language": e_lang, "tone": e_tone, "word_count_target": e_words}
                            _, err = api_patch(f"/scheduler/rules/{art_rid}", json=payload)
                            if err:
                                st.error(err)
                            else:
                                st.toast("Rule updated.")
                                st.rerun()
        else:
            st.info("No article rules. Add one below.")
        with st.expander("➕ Add article rule", expanded=(len(article_rules) == 0)):
            with st.form("add_art_rule"):
                name = st.text_input("Rule name", value="Daily articles", max_chars=256, key="add_art_name")
                interval_minutes = st.number_input("Interval (minutes)", min_value=1, max_value=525600, value=360, key="add_art_interval")
                articles_per_run = st.number_input("Articles per run", min_value=1, max_value=20, value=1, key="add_art_n")
                language = st.text_input("Language", value="en", max_chars=16, key="add_art_lang")
                tone = st.text_input("Tone", value="professional", max_chars=32, key="add_art_tone")
                word_count_target = st.number_input("Word count target", min_value=300, max_value=20000, value=1500, key="add_art_wc")
                if st.form_submit_button("Create article rule"):
                    payload = {
                        "rule_type": "articles",
                        "name": name,
                        "trigger_type": "interval",
                        "interval_minutes": interval_minutes,
                        "articles_per_run": articles_per_run,
                        "language": language,
                        "tone": tone,
                        "word_count_target": word_count_target,
                        "enabled": True,
                    }
                    out, e = api_post("/scheduler/rules", json=payload)
                    if e:
                        st.error(e)
                    else:
                        st.toast("Article rule created.")
                        st.rerun()

    with tab_jobs:
        st.subheader("Scheduled jobs")
        if not jobs:
            st.info("No scheduled jobs.")
        else:
            df_jobs = pd.DataFrame([
                {
                    "Job ID": j.get("id", ""),
                    "Type": j.get("type", "unknown"),
                    "Target ID": j.get("article_id") or j.get("keyword_id") or j.get("rule_id") or "—",
                    "Run at": format_short_date(j.get("run_at") or j.get("next_run_time")),
                }
                for j in jobs
            ])
            st.dataframe(df_jobs, use_container_width=True, hide_index=True)
            st.caption("Select a job to cancel it.")
            jsel, jbtn = st.columns([2, 1])
            with jsel:
                jopts = {f"#{j.get('id')} {j.get('type','')} · {j.get('article_id') or j.get('keyword_id') or j.get('rule_id')} · {format_short_date(j.get('run_at') or j.get('next_run_time'))}": j.get("id") for j in jobs}
                j_sel_label = st.selectbox("Job", list(jopts.keys()), key="job_sel", label_visibility="collapsed")
                j_id = jopts.get(j_sel_label) if j_sel_label else None
            with jbtn:
                if st.button("Cancel job", key="job_cancel_btn", disabled=not j_id):
                    ok, e = api_delete(f"/scheduler/jobs/{j_id}")
                    if e:
                        st.error(e)
                    else:
                        st.toast("Job cancelled.")
                        st.rerun()

    with tab_system:
        st.subheader("Scheduler status")
        with st.status("Scheduler", state="running" if (stats.get("total_jobs", 0) > 0 or active_rules > 0) else "complete"):
            st.write(f"Total jobs: {stats.get('total_jobs', 0)}")
            st.write(f"Next run: {format_short_date(stats.get('next_run')) or '—'}")
            st.write(f"Active recurring rules: {active_rules}")
        st.caption("Recurring jobs run automatically; one-time jobs run once at the scheduled time.")


def main():
    st.set_page_config(page_title="AI Content System", layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        """
        <style>
        /* Main content top padding */
        .block-container { padding-top: 1.5rem; }
        /* Sidebar nav buttons full width */
        [data-testid="stSidebar"] .stButton button { width: 100%; justify-content: center; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.title("AI Content System")
    try:
        with httpx.Client(timeout=5.0) as c:
            r = c.get(f"{BACKEND_URL}/health")
            if r.status_code == 200:
                st.sidebar.success("Backend connected")
            else:
                st.sidebar.error("Backend error")
    except Exception:
        st.sidebar.error("Backend unreachable")
    st.sidebar.caption(BACKEND_URL)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Navigation**")
    if "nav_page" not in st.session_state:
        st.session_state["nav_page"] = "articles"
    nav_items = [
        ("Articles", "articles"),
        ("Keywords", "keywords"),
        ("Calendar", "calendar"),
        ("Token usage", "usage"),
        ("AI settings", "settings"),
    ]
    for label, page_id in nav_items:
        if st.sidebar.button(label, key=f"nav_{page_id}", use_container_width=True, type="primary" if st.session_state["nav_page"] == page_id else "secondary"):
            st.session_state["nav_page"] = page_id
            st.rerun()
    current = st.session_state["nav_page"]
    if current == "articles":
        page_articles()
    elif current == "keywords":
        page_keywords()
    elif current == "usage":
        page_usage()
    elif current == "settings":
        page_settings()
    else:
        page_calendar()


if __name__ == "__main__":
    main()
