# 10 — نظام الجدولة (APScheduler)

## 1. الهدف

- جدولة نشر مقال في وقت محدد.
- جدولة توليد مقال لـ keyword في وقت محدد.
- (اختياري) مهام دورية: مثل مراجعة مقالات قديمة أو تشغيل توليد تلقائي لـ keywords معلقة.

---

## 2. الاختيار التقني

- **APScheduler** (مكتبة Python).
- نوع الـ scheduler: `BackgroundScheduler` أو `AsyncIOScheduler` حسب نوع تطبيق FastAPI (sync/async).
- تخزين المهام: في الذاكرة (بسيط) أو في قاعدة البيانات (مثلاً جدول `scheduled_jobs`) لاستمرار المهام بعد إعادة التشغيل.

---

## 3. المهام المطلوبة

| المهمة | الوصف | الاستدعاء |
|--------|--------|-----------|
| publish_article | نشر مقال محدد إلى WordPress في وقت مجدول | wordpress_service.publish_article(article_id) ثم تحديث status و published_at |
| generate_content | تشغيل pipeline التوليد لـ keyword في وقت مجدول | استدعاء الـ LangGraph workflow ثم حفظ المقال |
| (اختياري) update_old_articles | مراجعة أو إعادة تحسين مقالات قديمة | حسب تعريف المنتج |
| (اختياري) generate_from_queue | تشغيل توليد لـ N من keywords ذات status pending | استدعاء workflow لكل keyword |

---

## 4. التكامل مع FastAPI

- عند بدء التطبيق (`lifespan` أو `on_event("startup")`): تشغيل الـ scheduler.
- عند الإيقاف: إيقاف الـ scheduler بشكل نظيف.
- الـ API (راجع [05_API_DESIGN.md](05_API_DESIGN.md)) يضيف/يحذف مهام عبر دوال في `scheduler/publisher.py` تستخدم نفس الـ scheduler instance.

---

## 5. ملف `scheduler/publisher.py`

**المسؤوليات:**

- إنشاء instance من الـ scheduler.
- دوال مساعدة:
  - `schedule_publish(article_id, run_at: datetime)`
  - `schedule_generation(keyword_id, run_at: datetime)`
  - `cancel_job(job_id)`
  - `list_jobs()`
- تنفيذ المهمة الفعلية: استدعاء خدمة WordPress أو تشغيل الـ content generation graph وحفظ النتيجة في DB.

---

## 6. استمرار المهام بعد إعادة التشغيل

- إن استُخدمت مهام في الذاكرة فقط، إعادة تشغيل الخادم تفقد الجدولة.
- للحفاظ عليها: استخدام jobstore في APScheduler (مثل SQLAlchemyJobStore) مرتبط بنفس قاعدة البيانات، أو جدول `scheduled_jobs` مع استعادة المهام عند startup من الجدول وإضافتها إلى الـ scheduler.
