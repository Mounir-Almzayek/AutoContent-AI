# 07 — نماذج البيانات وقاعدة البيانات

## 1. قاعدة البيانات

- **التطوير:** SQLite (ملف واحد، لا إعداد إضافي).
- **الإنتاج (مقترح):** PostgreSQL.
- **ORM:** SQLAlchemy (نماذج في `models/` أو داخل `app/database.py` حسب التنظيم).

---

## 2. جدول المقالات (articles)

| العمود | النوع | الوصف |
|--------|--------|--------|
| id | PK, auto | معرف فريد |
| keyword_id | FK → keywords | الكلمة المفتاحية المرتبطة |
| title | string | عنوان المقال |
| content | text | المحتوى (HTML أو Markdown) |
| meta_title | string, nullable | عنوان الميتا |
| meta_description | string, nullable | وصف الميتا |
| status | enum/string | draft, generating, ready, published, failed |
| seo_score | float, nullable | درجة SEO من Quality/SEO agents |
| quality_score | float, nullable | درجة الجودة |
| wordpress_id | int, nullable | معرف المنشور في WordPress بعد النشر |
| published_at | datetime, nullable | وقت النشر الفعلي |
| created_at | datetime | وقت الإنشاء |
| updated_at | datetime | آخر تحديث |
| error_message | text, nullable | رسالة خطأ إن فشل التوليد أو النشر |

---

## 3. جدول الكلمات المفتاحية (keywords)

| العمود | النوع | الوصف |
|--------|--------|--------|
| id | PK, auto | معرف فريد |
| keyword | string, unique | الكلمة المفتاحية |
| topic | string, nullable | من Keyword Agent |
| search_intent | string, nullable | informational / transactional / navigational |
| status | enum/string | pending, processed, failed |
| created_at | datetime | وقت الإضافة |
| updated_at | datetime | آخر تحديث |

---

## 4. جدول استهلاك التوكينز (token_usage)

| العمود | النوع | الوصف |
|--------|--------|--------|
| id | PK, auto | معرف فريد |
| model | string | اسم النموذج (مثل openai/gpt-4o) |
| tokens_prompt | int | توكينز الإدخال |
| tokens_completion | int | توكينز الإخراج |
| total_tokens | int | المجموع |
| cost | decimal, nullable | التكلفة إن وُجدت |
| article_id | FK, nullable | المقال المرتبط إن وُجد |
| created_at | datetime | وقت الاستدعاء |

---

## 5. جدول الجدولة (scheduled_jobs) — اختياري

إن لم تُخزّن المهام داخل APScheduler فقط، يمكن جدول لتتبعها:

| العمود | النوع | الوصف |
|--------|--------|--------|
| id | PK | معرف المهمة (أو job_id من Scheduler) |
| type | string | publish / generate |
| article_id | FK, nullable | للمهام من نوع publish |
| keyword_id | FK, nullable | للمهام من نوع generate |
| scheduled_at | datetime | وقت التنفيذ المخطط |
| status | string | pending, running, completed, failed, cancelled |
| created_at | datetime | وقت إنشاء المهمة |

---

## 6. Pydantic Schemas (لـ API)

- **ArticleCreate, ArticleUpdate, ArticleResponse** — للمقالات.
- **KeywordCreate, KeywordResponse** — للكلمات المفتاحية.
- **GenerateRequest, GenerateResponse** — لـ POST /articles/generate.
- **TokenUsageResponse, UsageSummary** — لـ /usage/tokens و /usage/by-article.
- **AISettings** — لـ GET/PATCH /settings/ai.

يمكن وضعها في `models/article.py` و `models/keyword.py` أو في مجلد `api/schemas/` حسب تفضيل المشروع.
