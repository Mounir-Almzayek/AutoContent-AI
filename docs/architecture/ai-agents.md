# AI Agents Specification

Each agent is a node in the LangGraph with clear inputs and outputs.

---

## 1. Keyword Agent

**File:** `agents/keyword_agent.py`

| Item | Description |
|------|-------------|
| **Task** | Analyze the keyword and suggest long-tail variants and search intent |
| **Input** | `keyword: str` (and optional language/locale) |
| **Output** | `{ "topic", "search_intent", "related_keywords" }` |

**Output fields:**

- `topic`: Suggested main topic for the article.
- `search_intent`: informational / transactional / navigational.
- `related_keywords`: List of related or long-tail keywords.

**Implementation notes:**

- Use LLM via OpenRouter with a structured prompt.
- External calls (e.g. Google suggestions) can be added later.

---

## 2. Content Brief Agent

**File:** `agents/brief_agent.py`

| Item | Description |
|------|-------------|
| **Task** | Build the article plan (Content Brief) from keyword analysis |
| **Input** | Keyword Agent output + settings (length, language, tone) |
| **Output** | Structured brief: titles, outline, target keywords |

**Output fields:**

- `title`: Article title.
- `h1`: H1 heading.
- `h2`: List of H2 headings.
- `h3`: Nested H3 under each H2 (if any).
- `faq`: List of Q&A for the article.
- `target_keywords`: Target keywords for the content.
- `tone`: Tone (professional, friendly, technical, etc.).
- `word_count_target`: Target word count (optional).

---

## 3. Article Generator Agent

**File:** `agents/article_agent.py`

| Item | Description |
|------|-------------|
| **Task** | Generate full article text from the Brief |
| **Input** | Content Brief Agent output |
| **Output** | `content: str` (HTML or Markdown as agreed) |

**Implementation notes:**

- Call OpenRouter with a strong model (e.g. GPT-4 or Claude).
- Support `temperature` and `max_tokens` from settings.
- Log tokens used (prompt + completion).

---

## 4. Quality Checker Agent

**File:** `agents/quality_agent.py`

| Item | Description |
|------|-------------|
| **Task** | Check quality, structure, readability, and keyword density |
| **Input** | Article text + Brief (or target_keywords) |
| **Output** | Scores and recommendations |

**Output fields:**

- `readability_score`: Readability score.
- `keyword_density`: Keyword density ratio.
- `structure_ok`: Whether structure (H1, H2, H3) matches the Brief.
- `content_completeness`: Content coverage (e.g. percentage of points covered).
- `seo_score`: SEO score (0–100).
- `quality_score`: Overall quality score (0–100).
- `suggestions`: List of improvement suggestions (text).

---

## 5. Duplication Checker Agent

**File:** `agents/duplicate_agent.py`

| Item | Description |
|------|-------------|
| **Task** | Compare new article with existing ones for duplication |
| **Input** | New article text + (optional) list of titles/snippets or embeddings |
| **Output** | `is_duplicate: bool`, `similarity_score: float`, `most_similar_id` (if any) |

**Implementation options:**

1. **Embeddings:** Convert articles to vectors (sentence-transformers or OpenAI via OpenRouter) and compare cosine similarity. If `similarity > 0.8` → treat as duplicate.
2. **Title-only comparison:** Simpler first step (text or title embeddings).

**Notes:**

- Store embeddings for published articles to speed up future comparison.

---

## 6. SEO Optimizer Agent

**File:** `agents/seo_agent.py`

| Item | Description |
|------|-------------|
| **Task** | Optimize SEO elements in the final article |
| **Input** | Article + Brief (for reference) |
| **Output** | Optimized article + meta and linking suggestions |

**Output fields:**

- `optimized_content`: Text after optimization (title, H1, paragraphs, etc.).
- `meta_title`: Page title for meta.
- `meta_description`: Meta description (~155 characters).
- `internal_linking_suggestions`: Internal linking suggestions (text or structure).
- `faq_schema`: FAQ structure for schema.org (if Q&A exist).

---

## 7. Input/Output Summary Between Nodes

| From | To | Data passed |
|------|-----|-------------|
| Start | Keyword Agent | keyword, options |
| Keyword Agent | Brief Agent | topic, search_intent, related_keywords |
| Brief Agent | Article Agent | title, h1, h2, h3, faq, target_keywords, tone |
| Article Agent | Quality Agent | content + brief |
| Quality Agent | Duplicate Agent | content, article_id (if any) |
| Duplicate Agent | SEO Agent | content (if not duplicate) |
| SEO Agent | Save | optimized_content, meta_title, meta_description, faq_schema |

Graph design and the conditional after Duplicate are in [LangGraph Workflow](langgraph-workflow.md).
