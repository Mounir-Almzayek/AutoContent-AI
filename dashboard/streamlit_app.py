"""
Streamlit Dashboard: Content Calendar, Keywords, Articles, Token Usage, AI Settings.
See docs/06_DASHBOARD_SPEC.md. Connects to FastAPI backend at BACKEND_URL.
"""
import os
from datetime import datetime, timezone, timedelta

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

# OpenRouter models for AI Settings dropdown
OPENROUTER_MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "anthropic/claude-3-opus",
    "anthropic/claude-3-sonnet",
    "anthropic/claude-3-haiku",
    "mistralai/mixtral-8x7b-instruct",
    "meta-llama/llama-3-70b-instruct",
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
    """POST request. Returns (data, error_message)."""
    url = f"{API_BASE}{path}"
    try:
        with httpx.Client(timeout=120.0) as client:
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
    with st.spinner("Loading articles…"):
        data, err = api_get("/articles", params={"limit": 100})
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
    tab_list, tab_generate = st.tabs(["Article list", "Generate new article"])
    with tab_list:
        status_filter = st.selectbox("Filter by status", ["", "draft", "generating", "ready", "published", "failed"], key="art_status")
        filtered = [a for a in items if not status_filter or a.get("status") == status_filter]
        if not filtered:
            st.info("No articles yet. Use the **Generate new article** tab to create one.")
        else:
            for a in filtered:
                title = (a.get("title") or "Untitled")[:55]
                status = (a.get("status") or "draft").capitalize()
                with st.expander(f"{title} — {status}", expanded=False):
                    st.markdown(status_badge(a.get("status") or "draft"), unsafe_allow_html=True)
                    st.caption(f"ID {a.get('id')} · Created {format_short_date(a.get('created_at'))}")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("View details", key=f"view_{a['id']}"):
                            det, e = api_get(f"/articles/{a['id']}")
                            if e:
                                st.error(e)
                            else:
                                st.json(det)
                    with col2:
                        if status == "ready" and st.button("Publish to WordPress", key=f"pub_{a['id']}"):
                            with st.spinner("Publishing…"):
                                _, e = api_post(f"/articles/{a['id']}/publish")
                            if e:
                                st.error(e)
                            else:
                                st.success("Published")
                                st.rerun()
                    with col3:
                        confirm = st.checkbox("Confirm delete", key=f"confirm_del_{a['id']}")
                        if st.button("Delete", key=f"del_art_{a['id']}", disabled=not confirm):
                            ok, e = api_delete(f"/articles/{a['id']}")
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
    with st.spinner("Loading keywords…"):
        data, err = api_get("/keywords", params={"limit": 100})
    if err:
        st.error(err)
        return
    items = data.get("items") or []
    total = data.get("total") or 0
    st.metric("Total keywords", total)
    tab_list, tab_add, tab_import = st.tabs(["Keyword list", "Add keyword", "Import from file"])
    with tab_list:
        status_f = st.selectbox("Filter by status", ["", "pending", "processed", "failed"], key="kw_status")
        filtered = [k for k in items if not status_f or k.get("status") == status_f]
        if not filtered:
            st.info("No keywords yet. Use **Add keyword** or **Import from file** to add some.")
        else:
            for k in filtered:
                badge = status_badge(k.get("status") or "pending")
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{k.get('keyword', '')}** {badge} · ID {k.get('id')}", unsafe_allow_html=True)
                with col2:
                    if st.button("Delete", key=f"del_kw_{k['id']}"):
                        ok, e = api_delete(f"/keywords/{k['id']}")
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


def page_settings():
    st.title("AI Settings")
    with st.spinner("Loading…"):
        data, err = api_get("/settings/ai")
    if err:
        st.error(err)
        return
    with st.container():
        with st.form("ai_settings"):
            model = st.selectbox("Model", OPENROUTER_MODELS, index=OPENROUTER_MODELS.index(data.get("model", "openai/gpt-4o")) if data.get("model") in OPENROUTER_MODELS else 0, help="LLM used for generation.")
            temp = st.slider("Temperature", 0.0, 2.0, float(data.get("temperature", 0.7)), 0.1, help="Higher = more creative, lower = more focused.")
            max_tok = st.number_input("Max tokens", min_value=256, max_value=128000, value=int(data.get("max_tokens", 4096)), help="Max tokens per completion.")
            if st.form_submit_button("Save settings"):
                out, e = api_patch("/settings/ai", json={"model": model, "temperature": temp, "max_tokens": max_tok})
                if e:
                    st.error(e)
                else:
                    st.success("Settings saved. They will apply to the next generation.")


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
            by_date = _calendar_events_by_date(events)
            if not by_date:
                st.info("No events in the next 31 days. Schedule jobs or recurring rules to see them here.")
            else:
                for date_key in sorted(by_date.keys()):
                    with st.expander(f"📅 {date_key} ({len(by_date[date_key])} events)", expanded=(date_key == sorted(by_date.keys())[0])):
                        for e in by_date[date_key]:
                            typ = e.get("type", "job")
                            run_at = e.get("run_at", "")[:19]
                            if typ == "article":
                                st.markdown(f"**Article** · {e.get('status', '')} · {e.get('title', '') or e.get('id')} · {run_at}")
                            else:
                                jtype = e.get("job_type", "job")
                                rid = e.get("article_id") or e.get("keyword_id") or e.get("rule_id")
                                st.markdown(f"**Job** · {jtype} · ID `{rid}` · {run_at}")

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
        st.subheader("Recurring generation rules")
        st.caption("Configure automatic article generation: interval or cron, number of articles, keywords, and publish behavior (draft / immediate / delayed).")
        if rules:
            for r in rules:
                rid = r.get("id")
                en = r.get("enabled", True)
                trigger_str = _format_interval_minutes(r.get("interval_minutes")) if r.get("trigger_type") == "interval" else f"Cron: {r.get('cron_expression') or '—'}"
                pub_str = _format_publish_behavior(r.get("publish_behavior", "draft"), r.get("publish_delay_minutes"))
                with st.container():
                    st.markdown(f"**{r.get('name', 'Rule')}** " + ("🟢 Active" if en else "⏸ Paused"))
                    st.caption(
                        f"{trigger_str} · {r.get('articles_per_run')} articles/run · {pub_str} · "
                        f"Last: {format_short_date(r.get('last_run_at'))} ({r.get('last_articles_count') or 0} articles)"
                    )
                    rb1, rb2, rb3 = st.columns([1, 1, 2])
                    with rb1:
                        if st.button("Pause" if en else "Resume", key=f"rule_toggle_{rid}"):
                            path = f"/scheduler/rules/{rid}/pause" if en else f"/scheduler/rules/{rid}/resume"
                            _, e = api_post(path)
                            if e:
                                st.error(e)
                            else:
                                st.toast("Rule updated.")
                                st.rerun()
                    with rb2:
                        confirm_key = f"confirm_delete_rule_{rid}"
                        if st.session_state.get(confirm_key):
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("Yes, delete", key=f"del_yes_{rid}"):
                                    ok, err = api_delete(f"/scheduler/rules/{rid}")
                                    if err:
                                        st.error(err)
                                    else:
                                        if confirm_key in st.session_state:
                                            del st.session_state[confirm_key]
                                        st.toast("Rule deleted.")
                                        st.rerun()
                            with col_no:
                                if st.button("Cancel", key=f"del_no_{rid}"):
                                    if confirm_key in st.session_state:
                                        del st.session_state[confirm_key]
                                    st.rerun()
                        elif st.button("Delete", key=f"rule_del_{rid}"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    with st.expander("Edit rule", expanded=False):
                        with st.form(f"edit_rule_{rid}"):
                            e_name = st.text_input("Rule name", value=r.get("name", ""), max_chars=256, key=f"edit_name_{rid}")
                            e_trigger = st.radio("Trigger type", ["interval", "cron"], index=0 if r.get("trigger_type") == "interval" else 1, horizontal=True, key=f"edit_trigger_{rid}")
                            e_interval = st.number_input("Interval (minutes)", min_value=1, max_value=525600, value=r.get("interval_minutes") or 360, key=f"edit_interval_{rid}") if e_trigger == "interval" else None
                            e_cron = st.text_input("Cron (e.g. 0 9 * * *)", value=r.get("cron_expression") or "0 9 * * *", max_chars=128, key=f"edit_cron_{rid}") if e_trigger == "cron" else None
                            e_articles = st.number_input("Articles per run", min_value=1, max_value=20, value=r.get("articles_per_run", 1), key=f"edit_articles_{rid}")
                            e_kw_filter = st.radio("Keyword source", ["all_pending", "ids"], index=0 if r.get("keyword_filter") == "all_pending" else 1, horizontal=True, key=f"edit_kw_{rid}")
                            e_kw_ids = st.text_input("Keyword IDs (comma-separated)", value=r.get("keyword_ids") or "", key=f"edit_kw_ids_{rid}") if e_kw_filter == "ids" else None
                            e_lang = st.text_input("Language", value=r.get("language", "en"), max_chars=16, key=f"edit_lang_{rid}")
                            e_tone = st.text_input("Tone", value=r.get("tone", "professional"), max_chars=32, key=f"edit_tone_{rid}")
                            e_words = st.number_input("Word count target", min_value=300, max_value=20000, value=r.get("word_count_target", 1500), key=f"edit_words_{rid}")
                            e_pub = st.radio("After generation", ["draft", "immediate", "delay"], index=["draft", "immediate", "delay"].index(r.get("publish_behavior", "draft")), horizontal=True, key=f"edit_pub_{rid}")
                            e_delay = st.number_input("Publish delay (min)", min_value=0, max_value=10080, value=r.get("publish_delay_minutes") or 30, key=f"edit_delay_{rid}") if e_pub == "delay" else None
                            if st.form_submit_button("Save changes"):
                                payload = {"name": e_name, "trigger_type": e_trigger, "articles_per_run": e_articles, "keyword_filter": e_kw_filter, "language": e_lang, "tone": e_tone, "word_count_target": e_words, "publish_behavior": e_pub}
                                if e_trigger == "interval":
                                    payload["interval_minutes"] = e_interval or 360
                                    payload["cron_expression"] = None
                                else:
                                    payload["cron_expression"] = (e_cron or "").strip() or "0 9 * * *"
                                    payload["interval_minutes"] = None
                                if e_kw_filter == "ids":
                                    payload["keyword_ids"] = (e_kw_ids or "").strip()
                                if e_pub == "delay":
                                    payload["publish_delay_minutes"] = e_delay or 30
                                else:
                                    payload["publish_delay_minutes"] = None
                                _, err = api_patch(f"/scheduler/rules/{rid}", json=payload)
                                if err:
                                    st.error(err)
                                else:
                                    st.toast("Rule updated.")
                                    st.rerun()
                    st.divider()
        else:
            st.info("No recurring rules. Add one below.")
        with st.expander("➕ Add recurring rule", expanded=(len(rules) == 0)):
            with st.form("add_rule"):
                name = st.text_input("Rule name", value="Daily content", max_chars=256)
                trigger_type = st.radio("Trigger type", ["interval", "cron"], format_func=lambda x: "Interval (every X minutes)" if x == "interval" else "Cron (e.g. 0 9 * * *)", horizontal=True)
                interval_minutes = st.number_input("Interval (minutes)", min_value=1, max_value=525600, value=360, key="rule_interval") if trigger_type == "interval" else None
                cron_expression = st.text_input("Cron expression (5 fields: min hour day month dow)", value="0 9 * * *", max_chars=128, key="rule_cron", placeholder="0 9 * * *") if trigger_type == "cron" else None
                articles_per_run = st.number_input("Articles per run", min_value=1, max_value=20, value=1)
                keyword_filter = st.radio("Keyword source", ["all_pending", "ids"], format_func=lambda x: "All pending keywords" if x == "all_pending" else "Specific keyword IDs", horizontal=True)
                if keyword_filter == "ids":
                    keyword_ids = st.text_input("Keyword IDs (comma-separated)", value="", key="rule_kw_ids")
                    st.caption("Enter at least one keyword ID for generation to run.")
                else:
                    keyword_ids = None
                language = st.text_input("Language", value="en", max_chars=16)
                tone = st.text_input("Tone", value="professional", max_chars=32)
                word_count_target = st.number_input("Word count target", min_value=300, max_value=20000, value=1500)
                publish_behavior = st.radio("After generation", ["draft", "immediate", "delay"], format_func=lambda x: "Save as draft only" if x == "draft" else "Publish immediately" if x == "immediate" else "Publish after delay", horizontal=True)
                publish_delay_minutes = st.number_input("Publish delay (minutes)", min_value=0, max_value=10080, value=30, key="rule_delay") if publish_behavior == "delay" else None
                if st.form_submit_button("Create rule"):
                    if trigger_type == "cron" and (not cron_expression or not str(cron_expression).strip()):
                        st.error("Cron expression is required when trigger type is Cron.")
                    else:
                        payload = {
                            "name": name,
                            "trigger_type": trigger_type,
                            "articles_per_run": articles_per_run,
                            "keyword_filter": keyword_filter,
                            "language": language,
                            "tone": tone,
                            "word_count_target": word_count_target,
                            "publish_behavior": publish_behavior,
                            "enabled": True,
                        }
                        if trigger_type == "interval" and interval_minutes:
                            payload["interval_minutes"] = interval_minutes
                        if trigger_type == "cron" and cron_expression:
                            payload["cron_expression"] = str(cron_expression).strip()
                        if keyword_filter == "ids" and keyword_ids is not None:
                            payload["keyword_ids"] = str(keyword_ids).strip()
                        if publish_behavior == "delay" and publish_delay_minutes is not None:
                            payload["publish_delay_minutes"] = publish_delay_minutes
                        out, e = api_post("/scheduler/rules", json=payload)
                        if e:
                            st.error(e)
                        else:
                            st.toast("Rule created.")
                            st.rerun()

    with tab_jobs:
        st.subheader("Scheduled jobs")
        if not jobs:
            st.info("No scheduled jobs.")
        else:
            for j in jobs:
                t = j.get("type", "unknown")
                rid = j.get("article_id") or j.get("keyword_id") or j.get("rule_id") or "—"
                run_at = j.get("run_at") or j.get("next_run_time")
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{t}** · Target `{rid}` · {format_short_date(run_at) if run_at else '—'}")
                with c2:
                    if st.button("Cancel", key=f"cancel_{j.get('id')}"):
                        ok, e = api_delete(f"/scheduler/jobs/{j['id']}")
                        if e:
                            st.error(e)
                        else:
                            st.toast("Job cancelled.")
                            st.rerun()
                st.divider()

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
        /* Sidebar: current selection and spacing */
        [data-testid="stSidebar"] [role="radiogroup"] label { padding: 0.5rem 0.75rem; border-radius: 0.5rem; margin-bottom: 0.2rem; }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(151,166,195,0.12); }
        [data-testid="stSidebar"] [role="radiogroup"] label div:first-child { font-weight: 500; }
        /* Main content top padding */
        .block-container { padding-top: 1.5rem; }
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
    st.sidebar.markdown("**Content** · **System**")
    page = st.sidebar.radio(
        "Navigation",
        ["📄 Articles", "🔑 Keywords", "📅 Calendar", "📊 Token usage", "⚙️ AI settings"],
        label_visibility="collapsed",
    )
    page_map = {"📄 Articles": "articles", "🔑 Keywords": "keywords", "📅 Calendar": "calendar", "📊 Token usage": "usage", "⚙️ AI settings": "settings"}
    current = page_map.get(page, "articles")
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
