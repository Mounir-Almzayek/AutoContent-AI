# 09 — التكامل مع WordPress REST API

## 1. المتطلبات

- موقع WordPress مع تفعيل REST API (متوفر افتراضياً في الإصدارات الحديثة).
- مستخدم بتصريح "نشر" (مثلاً Editor أو Administrator).
- تطبيق كلمة مرور (Application Password) أو استخدام Basic Auth مع المستخدم وكلمة المرور.

---

## 2. الإعداد (Config)

| المتغير | الوصف |
|---------|--------|
| WORDPRESS_URL | عنوان الموقع (مثل https://example.com) |
| WORDPRESS_USER | اسم المستخدم |
| WORDPRESS_APP_PASSWORD | كلمة مرور التطبيق (Application Password) |
| WORDPRESS_DEFAULT_STATUS | status للنشر: draft / publish / private |

---

## 3. Endpoint النشر

- **POST** `{WORDPRESS_URL}/wp-json/wp/v2/posts`

**Headers:**

- `Content-Type: application/json`
- `Authorization: Basic base64(user:app_password)`

**Body (أساسي):**

```json
{
  "title": "عنوان المقال",
  "content": "المحتوى HTML أو block markup",
  "status": "publish",
  "categories": [1, 2],
  "tags": [3, 4]
}
```

---

## 4. خدمة WordPress (`services/wordpress_service.py`)

**المسؤوليات:**

- بناء الـ URL والـ headers من الإعدادات.
- دالة `publish_article(article_id)` أو `publish_article(title, content, meta_title, meta_description, categories, tags)`:
  - إرسال POST إلى `/wp/v2/posts`.
  - في حالة النجاح: حفظ `wordpress_id` و `published_at` في جدول المقالات.
  - في حالة الفشل: تحديث `status` إلى failed وحفظ `error_message`.

- (اختياري) دوال لاحقة: تحديث منشور (PUT)، حذف، جلب التصنيفات/الوسوم (GET) لاستخدامها في الـ Dashboard.

---

## 5. التصنيفات والوسوم

- للحصول على قائمة التصنيفات: GET `{WORDPRESS_URL}/wp-json/wp/v2/categories`.
- للحصول على قائمة الوسوم: GET `{WORDPRESS_URL}/wp-json/wp/v2/tags`.
- يمكن إضافة حقول في جدول المقالات أو في الإعدادات: `default_category_id`, `default_tag_ids` لاستخدامها عند النشر إن لم يحدد المستخدم غيرها.
