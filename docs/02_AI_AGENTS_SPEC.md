# 02 — مواصفات الـ AI Agents

كل Agent عبارة عن عقدة (Node) في LangGraph لها مدخلات ومخرجات واضحة.

---

## 1. Keyword Agent

**الملف المقترح:** `agents/keyword_agent.py`

| البند | الوصف |
|-------|--------|
| **المهمة** | تحليل الكلمة المفتاحية واقتراح long-tail وتحديد search intent |
| **المدخل** | `keyword: str` (ومعلومات اختيارية مثل اللغة/الموقع) |
| **المخرج** | `{ "topic", "search_intent", "related_keywords" }` |

**الحقول المقترحة للمخرج:**

- `topic`: موضوع رئيسي مقترح للمقال.
- `search_intent`: informational / transactional / navigational.
- `related_keywords`: قائمة كلمات مفتاحية مرتبطة أو long-tail.

**ملاحظات التنفيذ:**

- استخدام LLM عبر OpenRouter مع prompt منظم.
- يمكن دعم استدعاء خارجي (مثل اقتراحات Google) لاحقاً.

---

## 2. Content Brief Agent

**الملف المقترح:** `agents/brief_agent.py`

| البند | الوصف |
|-------|--------|
| **المهمة** | بناء خطة المقال (Content Brief) بناءً على تحليل الكلمة المفتاحية |
| **المدخل** | مخرجات Keyword Agent + إعدادات (طول، لغة، نبرة) |
| **المخرج** | بنية محددة للمقال: عناوين، هيكل، كلمات مستهدفة |

**الحقول المقترحة للمخرج:**

- `title`: عنوان المقال.
- `h1`: عنوان H1.
- `h2`: قائمة عناوين H2.
- `h3`: قامة متداخلة H3 تحت كل H2 (إن وجد).
- `faq`: قائمة أسئلة وأجوبة للمقال.
- `target_keywords`: كلمات مفتاحية مستهدفة في المحتوى.
- `tone`: نبرة (احترافي، ودود، تقني، إلخ).
- `word_count_target`: عدد الكلمات المستهدف (اختياري).

---

## 3. Article Generator Agent

**الملف المقترح:** `agents/article_agent.py`

| البند | الوصف |
|-------|--------|
| **المهمة** | توليد نص المقال الكامل وفق الـ Brief |
| **المدخل** | مخرجات Content Brief Agent |
| **المخرج** | `content: str` (HTML أو Markdown حسب الاتفاق) |

**ملاحظات التنفيذ:**

- استدعاء OpenRouter مع نموذج قوي (مثل GPT-4 أو Claude).
- دعم `temperature` و `max_tokens` من الإعدادات.
- تسجيل التوكينز المستهلكة (prompt + completion).

---

## 4. Quality Checker Agent

**الملف المقترح:** `agents/quality_agent.py`

| البند | الوصف |
|-------|--------|
| **المهمة** | فحص الجودة والهيكل وقراءة النص وكثافة الكلمات المفتاحية |
| **المدخل** | المقال النصي + الـ Brief (أو target_keywords) |
| **المخرج** | درجات وتوصيات |

**الحقول المقترحة للمخرج:**

- `readability_score`: درجة قابلية القراءة.
- `keyword_density`: نسبة الكلمات المفتاحية.
- `structure_ok`: هل الهيكل (H1, H2, H3) مطابق للـ Brief.
- `content_completeness`: اكتمال المحتوى (مثلاً نسبة تغطية النقاط).
- `seo_score`: درجة SEO (0–100).
- `quality_score`: درجة جودة عامة (0–100).
- `suggestions`: قائمة تحسينات مقترحة (نص).

---

## 5. Duplication Checker Agent

**الملف المقترح:** `agents/duplicate_agent.py`

| البند | الوصف |
|-------|--------|
| **المهمة** | مقارنة المقال الجديد مع المقالات السابقة لاكتشاف التكرار |
| **المدخل** | نص المقال الجديد + (اختياري) قائمة عناوين/أوصاف المقالات السابقة أو embeddings |
| **المخرج** | `is_duplicate: bool`, `similarity_score: float`, `most_similar_id` (إن وجد) |

**طرق التنفيذ المقترحة:**

1. **Embeddings:** تحويل المقالات إلى vectors (sentence-transformers أو OpenAI embeddings عبر OpenRouter) ومقارنة cosine similarity. إذا `similarity > 0.8` → اعتبار المقال مكرراً.
2. **مقارنة بالعناوين فقط:** كخطوة أولى بسيطة (نص أو embedding للعناوين).

**ملاحظات:**

- تخزين embeddings للمقالات المنشورة لتسريع المقارنة لاحقاً.

---

## 6. SEO Optimizer Agent

**الملف المقترح:** `agents/seo_agent.py`

| البند | الوصف |
|-------|--------|
| **المهمة** | تحسين عناصر SEO في المقال النهائي |
| **المدخل** | المقال + الـ Brief (للمرجع) |
| **المخرج** | نسخة محسّنة من المقال + meta واقتراحات ربط |

**الحقول المقترحة للمخرج:**

- `optimized_content`: النص بعد التحسين (عنوان، H1، فقرات، إلخ).
- `meta_title`: عنوان الصفحة للميتا.
- `meta_description`: وصف الميتا (حوالي 155 حرفاً).
- `internal_linking_suggestions`: اقتراحات ربط داخلي (نص أو بنية).
- `faq_schema`: بنية FAQ للـ schema.org (إن وُجدت أسئلة وأجوبة).

---

## 7. ملخص المدخلات والمخرجات بين العقد

| من | إلى | البيانات المارة |
|----|-----|------------------|
| Start | Keyword Agent | keyword, options |
| Keyword Agent | Brief Agent | topic, search_intent, related_keywords |
| Brief Agent | Article Agent | title, h1, h2, h3, faq, target_keywords, tone |
| Article Agent | Quality Agent | content + brief |
| Quality Agent | Duplicate Agent | content, article_id (إن وُجد) |
| Duplicate Agent | SEO Agent | content (إن لم يكن مكرراً) |
| SEO Agent | Save | optimized_content, meta_title, meta_description, faq_schema |

التصميم التفصيلي للـ Graph والشرط (conditional) بعد Duplicate في [03_LANGGRAPH_WORKFLOW.md](03_LANGGRAPH_WORKFLOW.md).
