# نظام توليد ونشر المقالات بالذكاء الاصطناعي

نظام متكامل لتوليد مقالات مدعومة بالـ AI، مراجعتها، وتحسينها ثم نشرها إلى WordPress.

## المعمارية

- **Dashboard:** Streamlit — إدارة الكلمات المفتاحية، الجدولة، الإعدادات، مراقبة التوكينز.
- **Backend:** FastAPI — API، إدارة DB، تشغيل الـ AI workflow، جدولة النشر.
- **AI Engine:** LangGraph + OpenRouter — pipeline من العقد (Keyword → Brief → Article → Quality → Duplicate → SEO).
- **النشر:** WordPress REST API.

## هيكل المشروع

```
├── app/           # نقطة الدخول، config، database
├── api/            # مسارات FastAPI
├── agents/         # عقد الـ AI (keyword, brief, article, quality, duplicate, seo)
├── graphs/         # LangGraph workflow
├── services/       # OpenRouter، WordPress، Token Tracker
├── scheduler/      # APScheduler للنشر والتوليد
├── dashboard/      # تطبيق Streamlit
├── models/         # نماذج البيانات
└── docs/           # الوثائق والخطط
```

## الوثائق

جميع الخطط والمواصفات في مجلد **docs/**:

- [فهرس الوثائق](docs/README.md)
- [نظرة المعمارية](docs/01_ARCHITECTURE_OVERVIEW.md)
- [مواصفات الـ Agents](docs/02_AI_AGENTS_SPEC.md)
- [LangGraph Workflow](docs/03_LANGGRAPH_WORKFLOW.md)
- [المراحل والجدول الزمني](docs/04_PHASES_AND_ROADMAP.md)
- [تصميم API](docs/05_API_DESIGN.md)
- [مواصفات Dashboard](docs/06_DASHBOARD_SPEC.md)
- [نماذج البيانات](docs/07_DATA_MODELS.md)
- [OpenRouter](docs/08_OPENROUTER_INTEGRATION.md)
- [WordPress](docs/09_WORDPRESS_INTEGRATION.md)
- [الجدولة](docs/10_SCHEDULER_SPEC.md)

## البدء

1. نسخ `.env.example` إلى `.env` وتعبئة القيم.
2. تثبيت الاعتماديات: `pip install -r requirements.txt`
3. تشغيل الـ Backend: من جذر المشروع (وفق تهيئة المشروع لاحقاً).
4. تشغيل الـ Dashboard: `streamlit run dashboard/streamlit_app.py`

التطوير حسب المراحل الموضحة في **docs/04_PHASES_AND_ROADMAP.md**.
