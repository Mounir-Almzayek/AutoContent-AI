# 08 — التكامل مع OpenRouter وتتبع التوكينز

## 1. OpenRouter كـ Gateway

- **الاستخدام:** استدعاء نماذج LLM عبر واجهة واحدة (OpenRouter API).
- **الميزة:** تغيير النموذج (GPT-4، Claude، Mixtral، Llama، إلخ) دون تغيير الكود، فقط تغيير `model` في الإعدادات.

---

## 2. الإعداد (Config)

| المتغير | الوصف |
|---------|--------|
| OPENROUTER_API_KEY | مفتاح API من openrouter.ai |
| OPENROUTER_BASE_URL | اختياري، الافتراضي https://openrouter.ai/api/v1 |
| DEFAULT_MODEL | النموذج الافتراضي (مثل openai/gpt-4o أو anthropic/claude-3-opus) |
| DEFAULT_TEMPERATURE | 0.0 – 2.0 |
| DEFAULT_MAX_TOKENS | حد أقصى لتوكينز الإخراج |

---

## 3. خدمة OpenRouter (`services/openrouter_service.py`)

**المسؤوليات:**

- إرسال طلبات Chat Completion إلى OpenRouter.
- دعم معلمات: `model`, `messages`, `temperature`, `max_tokens`.
- قراءة النموذج من الإعدادات أو من معلمة الطلب (override).
- إرجاع النص + (إن أمكن) استخدام التوكينز من الاستجابة لتسجيلها في Token Tracker.

**واجهة مقترحة:**

- `chat(messages, model=None, temperature=None, max_tokens=None) -> (content: str, usage: dict)`
- `usage` يحتوي على: `prompt_tokens`, `completion_tokens`, `total_tokens` (وإن وُجدت تكلفة من OpenRouter تُمرر إلى token_tracker).

---

## 4. تتبع التوكينز (`services/token_tracker.py`)

**المسؤوليات:**

- تسجيل كل استدعاء: `model`, `tokens_prompt`, `tokens_completion`, `total_tokens`, `cost`, `article_id` (اختياري), `timestamp`.
- دوال استعلام:
  - حسب الفترة (يوم، أسبوع، شهر).
  - حسب المقال (استهلاك لكل article_id).
  - إجمالي التكلفة لفترة.

الجدول المقترح في [07_DATA_MODELS.md](07_DATA_MODELS.md) (جدول `token_usage`).

---

## 5. نماذج مدعومة (أمثلة)

يمكن الاحتفاظ بقائمة ثابتة في الـ Dashboard أو جلبها من OpenRouter:

- `openai/gpt-4o`
- `openai/gpt-4o-mini`
- `anthropic/claude-3-opus`
- `anthropic/claude-3-sonnet`
- `anthropic/claude-3-haiku`
- `mistralai/mixtral-8x7b-instruct`
- `meta-llama/llama-3-70b-instruct`

المستخدم يختار من الـ Dashboard ويُحفظ في الإعدادات (DB أو ملف)، والـ Backend يقرأها عند كل استدعاء لـ OpenRouter.
