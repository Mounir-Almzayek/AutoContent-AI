# 03 — تصميم LangGraph Workflow

## 1. مخطط الـ Graph

```
                    ┌─────────────┐
                    │    START    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  keyword_   │
                    │  analyzer   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   content   │
                    │   _brief    │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  article_   │
                    │  generator  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  quality_   │
                    │   check     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  duplicate_ │
                    │   check     │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │  is_dup?    │
                    └──────┬──────┘
                    ┌──────┴──────┐
                   YES            NO
                    │              │
                    ▼              ▼
             ┌──────────┐   ┌─────────────┐
             │  REJECT  │   │ seo_        │
             │ (optional│   │ optimizer   │
             │  retry)  │   └──────┬──────┘
             └──────────┘         │
                                  ▼
                           ┌─────────────┐
                           │ save_       │
                           │ article     │
                           └──────┬──────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │    END      │
                           └─────────────┘
```

---

## 2. حالة الـ Graph (State)

يُقترح استخدام **State** موحّد يمر عبر كل العقد. الحقول المقترحة:

| الحقل | النوع | الوصف |
|-------|--------|--------|
| `keyword` | str | الكلمة المفتاحية المدخلة |
| `keyword_analysis` | dict | مخرجات Keyword Agent |
| `brief` | dict | مخرجات Content Brief Agent |
| `content` | str | نص المقال (خام أو محسّن) |
| `quality_result` | dict | مخرجات Quality Checker |
| `is_duplicate` | bool | نتيجة Duplicate Checker |
| `duplicate_similarity` | float | أعلى تشابه مع مقال سابق |
| `seo_result` | dict | مخرجات SEO Optimizer |
| `article_id` | str/int | معرف المقال بعد الحفظ (إن وُجد) |
| `error` | str | رسالة خطأ إن فشلت أي عقدة |
| `current_node` | str | اسم العقدة الحالية (للتتبع) |

---

## 3. التفرع الشرطي (Conditional Edges)

- **بعد duplicate_check:**  
  - إذا `is_duplicate == True` → الانتقال إلى عقدة **reject** (أو إعادة المحاولة بكلمة مختلفة حسب التصميم).  
  - إذا `is_duplicate == False` → الانتقال إلى **seo_optimizer**.

- **بعد quality_check (اختياري):**  
  - إذا `quality_score` أقل من حد معين → يمكن إما إعادة التوليد أو المتابعة مع تحذير (حسب المنتج).

---

## 4. الملف المسؤول عن الـ Graph

| الملف | المسؤولية |
|-------|-----------|
| `graphs/content_generation_graph.py` | تعريف الـ State، إضافة العقد، تعريف الـ edges (العادية والشرطية)، بناء الـ CompiledGraph وتصديره |

---

## 5. استدعاء الـ Graph من الـ Backend

- الـ Backend (FastAPI) يستدعي دالة مثل:  
  `run_content_generation(keyword, options)`.
- الدالة تُنشئ الـ graph (أو تستخدم instance مُعد مسبقاً)، وتستدعي `graph.invoke(initial_state)`.
- النتيجة النهائية (بما فيها `article_id` أو `error`) تُعاد إلى الـ API.

---

## 6. التعامل مع الأخطاء

- أي عقدة يمكن أن تضع `error` في الـ State وتوقف التقدم (عقدة نهائية "failure").
- إعادة المحاولة (retry) يمكن تنفيذها على مستوى استدعاء LLM داخل الـ Agent أو على مستوى العقدة حسب السياسة المختارة.
