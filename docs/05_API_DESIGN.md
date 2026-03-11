# 05 — تصميم واجهات FastAPI

## 1. القواعد العامة

- **Base URL:** `/api/v1` (أو بدون نسخة حسب الاختيار).
- **التوثيق:** تفعيل Swagger UI و ReDoc من FastAPI.
- **الاستجابة الموحدة:** استخدام Pydantic models للـ response (قوائم، عنصر واحد، رسائل خطأ).

---

## 2. المقالات (Articles)

| Method | Endpoint | الوصف |
|--------|----------|--------|
| GET | `/articles` | قائمة مقالات (فلترة: status، تاريخ، صفحة، حد) |
| GET | `/articles/{id}` | تفاصيل مقال واحد |
| POST | `/articles` | إنشاء مقال يدوي (بدون AI) — اختياري |
| POST | `/articles/generate` | تشغيل pipeline التوليد (body: keyword، options) |
| PATCH | `/articles/{id}` | تحديث (مثلاً status، title، content) |
| DELETE | `/articles/{id}` | حذف مقال |
| POST | `/articles/{id}/publish` | إطلاق نشر المقال إلى WordPress |

**مثال body لـ POST /articles/generate:**

```json
{
  "keyword": "أفضل أدوات التسويق الرقمي",
  "options": {
    "language": "ar",
    "tone": "professional",
    "word_count_target": 1500,
    "model_override": "openai/gpt-4o"
  }
}
```

---

## 3. الكلمات المفتاحية (Keywords)

| Method | Endpoint | الوصف |
|--------|----------|--------|
| GET | `/keywords` | قائمة كلمات مفتاحية (فلترة، صفحة) |
| GET | `/keywords/{id}` | تفاصيل كلمة مفتاحية |
| POST | `/keywords` | إضافة كلمة/كلمات |
| POST | `/keywords/import` | استيراد من ملف (csv/txt) |
| PATCH | `/keywords/{id}` | تعديل |
| DELETE | `/keywords/{id}` | حذف |

---

## 4. الجدولة (Scheduler)

| Method | Endpoint | الوصف |
|--------|----------|--------|
| GET | `/scheduler/jobs` | قائمة المهام المجدولة |
| POST | `/scheduler/schedule-article` | جدولة نشر مقال في وقت محدد (article_id، scheduled_at) |
| POST | `/scheduler/schedule-generation` | جدولة توليد مقال لـ keyword في وقت محدد |
| DELETE | `/scheduler/jobs/{job_id}` | إلغاء مهمة |
| GET | `/scheduler/stats` | إحصائيات (عدد المهام، التالي، إلخ) |

---

## 5. التوكينز والإعدادات (Token Usage & AI Settings)

| Method | Endpoint | الوصف |
|--------|----------|--------|
| GET | `/usage/tokens` | استهلاك التوكينز (query: period=day|month، من-إلى) |
| GET | `/usage/by-article` | استهلاك لكل مقال (اختياري) |
| GET | `/settings/ai` | إعدادات AI الحالية (نموذج، temperature، max_tokens) |
| PATCH | `/settings/ai` | تحديث إعدادات AI |

---

## 6. الصحة والجاهزية

| Method | Endpoint | الوصف |
|--------|----------|--------|
| GET | `/health` | صحة الخدمة (وصول DB، اختياري: OpenRouter) |
| GET | `/ready` | جاهزية للاستقبال طلبات |

---

## 7. ربط الـ Routes في `app/main.py`

- تضمين routers من `api/routes_articles`، `routes_keywords`، `routes_scheduler`.
- إضافة prefix مثل `prefix="/api/v1"`.
- توثيق التصنيفات (tags) لتنظيم Swagger: Articles، Keywords，Scheduler، Usage، Settings.

تفاصيل نماذج الطلب/الاستجابة في [07_DATA_MODELS.md](07_DATA_MODELS.md).
