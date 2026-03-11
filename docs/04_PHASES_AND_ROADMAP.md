# 04 — المراحل والجدول الزمني والملفات

## 1. نظرة عامة على المراحل

| المرحلة | الاسم | الهدف الرئيسي | المخرجات |
|---------|--------|----------------|----------|
| **0** | البنية والوثائق | هيكل المشروع + الوثائق | مجلدات، ملفات، docs |
| **1** | الأساس (Config, DB, OpenRouter) | بيئة تشغيل واتصال LLM | config، DB، openrouter_service، token_tracker |
| **2** | الـ Agents والـ Graph | تنفيذ العقد والـ workflow | agents/*، graphs/* |
| **3** | Backend API | FastAPI + routes | app/main، api/*، models |
| **4** | الجدولة والـ WordPress | نشر وجدولة | scheduler/*، wordpress_service |
| **5** | Dashboard | واجهة Streamlit | dashboard/* |
| **6** | التحسين والاختبار | جودة، مراقبة، توثيق | tests، تحسينات |

---

## 2. هيكل الملفات والمجلدات الكامل

```
ai-content-system/
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # إعدادات (env، نموذج، إلخ)
│   └── database.py          # اتصال DB وجداول
│
├── api/
│   ├── __init__.py
│   ├── routes_articles.py    # CRUD مقالات + تشغيل التوليد
│   ├── routes_keywords.py   # إدارة الكلمات المفتاحية
│   └── routes_scheduler.py  # جدولة ومهام
│
├── agents/
│   ├── __init__.py
│   ├── keyword_agent.py
│   ├── brief_agent.py
│   ├── article_agent.py
│   ├── quality_agent.py
│   ├── duplicate_agent.py
│   └── seo_agent.py
│
├── graphs/
│   ├── __init__.py
│   └── content_generation_graph.py
│
├── services/
│   ├── __init__.py
│   ├── openrouter_service.py   # استدعاء OpenRouter
│   ├── wordpress_service.py    # نشر إلى WordPress
│   └── token_tracker.py        # تسجيل واستعلام التوكينز
│
├── scheduler/
│   ├── __init__.py
│   └── publisher.py            # مهام النشر والتوليد
│
├── dashboard/
│   ├── __init__.py
│   └── streamlit_app.py        # تطبيق Streamlit
│
├── models/
│   ├── __init__.py
│   ├── article.py              # نموذج المقال (DB + Pydantic)
│   └── keyword.py              # نموذج الكلمة المفتاحية
│
├── docs/                        # الوثائق (هذا المجلد)
│   ├── README.md
│   ├── 01_ARCHITECTURE_OVERVIEW.md
│   ├── 02_AI_AGENTS_SPEC.md
│   ├── 03_LANGGRAPH_WORKFLOW.md
│   ├── 04_PHASES_AND_ROADMAP.md
│   ├── 05_API_DESIGN.md
│   ├── 06_DASHBOARD_SPEC.md
│   ├── 07_DATA_MODELS.md
│   ├── 08_OPENROUTER_INTEGRATION.md
│   ├── 09_WORDPRESS_INTEGRATION.md
│   └── 10_SCHEDULER_SPEC.md
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. تفصيل الملفات حسب المرحلة

### المرحلة 0 — البنية والوثائق (حالي)

- إنشاء المجلدات أعلاه.
- إنشاء جميع ملفات `docs/`.
- إنشاء `requirements.txt` و `.env.example` و `README.md` أساسي.
- إضافة `__init__.py` في كل package.

### المرحلة 1 — الأساس

| الملف | المهمة |
|-------|--------|
| `app/config.py` | قراءة env (OPENROUTER_API_KEY، DB_URL، WORDPRESS_*، إلخ) |
| `app/database.py` | SQLAlchemy engine، session، تعريف الجداول (أو استيرادها من models) |
| `models/article.py` | جدول/نموذج المقال + Pydantic schemas |
| `models/keyword.py` | جدول/نموذج الكلمة المفتاحية + Pydantic |
| `services/openrouter_service.py` | دالة استدعاء LLM (chat completion) عبر OpenRouter |
| `services/token_tracker.py` | تسجيل (model, tokens_in, tokens_out, cost, timestamp) واستعلام إحصائيات |

### المرحلة 2 — الـ Agents والـ Graph

| الملف | المهمة |
|-------|--------|
| `agents/keyword_agent.py` | منطق Keyword Agent واستدعاء OpenRouter |
| `agents/brief_agent.py` | منطق Content Brief |
| `agents/article_agent.py` | توليد المقال |
| `agents/quality_agent.py` | فحص الجودة وإرجاع scores |
| `agents/duplicate_agent.py` | مقارنة embeddings أو عناوين |
| `agents/seo_agent.py` | تحسين SEO وmeta |
| `graphs/content_generation_graph.py` | State + عقد + edges + conditional + compile |

### المرحلة 3 — Backend API

| الملف | المهمة |
|-------|--------|
| `app/main.py` | FastAPI app، CORS، تضمين routers |
| `api/routes_articles.py` | POST/GET/PATCH مقالات، تشغيل pipeline |
| `api/routes_keywords.py` | CRUD keywords |
| `api/routes_scheduler.py` | جدولة، قائمة مهام، إعدادات |

### المرحلة 4 — الجدولة والـ WordPress

| الملف | المهمة |
|-------|--------|
| `services/wordpress_service.py` | POST /wp/v2/posts، إعدادات الموقع |
| `scheduler/publisher.py` | APScheduler، مهام publish_article، generate_new_content |

### المرحلة 5 — Dashboard

| الملف | المهمة |
|-------|--------|
| `dashboard/streamlit_app.py` | صفحات: Content Calendar، Keywords، Articles، Token Usage، AI Settings |

### المرحلة 6 — التحسين

- إضافة مجلد `tests/` واختبارات وحدة وتكامل.
- تحسين معالجة الأخطاء والـ logging.
- توثيق API (OpenAPI) وقراءة الوثائق من `docs/`.

---

## 4. ترتيب التطوير الموصى به

1. **0** → إنشاء الهيكل والوثائق (كما هو موثق هنا).
2. **1** → config، database، models، openrouter_service، token_tracker.
3. **2** → agents واحداً تلو الآخر ثم الـ graph.
4. **3** → main + routes (articles أولاً ثم keywords ثم scheduler).
5. **4** → wordpress_service ثم scheduler.
6. **5** → dashboard يربط مع الـ API.
7. **6** → اختبارات وتحسينات.

---

## 5. الاعتماديات (ملخص لـ requirements.txt)

- `fastapi`, `uvicorn`
- `streamlit`
- `langgraph`, `langchain-core` (أو ما يلزم لـ LangGraph)
- `httpx` أو `requests` (OpenRouter، WordPress)
- `sqlalchemy`, محرك DB (مثل `asyncpg` إن استخدمت async)
- `apscheduler`
- `pydantic`, `pydantic-settings`
- `python-dotenv`
- (اختياري) `sentence-transformers` أو مكتبة embeddings للـ duplicate check

التفاصيل في كل وثيقة مرتبطة (API، نماذج البيانات، OpenRouter، إلخ).
