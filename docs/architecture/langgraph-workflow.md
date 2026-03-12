# LangGraph Workflow Design

## 1. Graph Diagram

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

## 2. Graph State

A single **State** object is passed through all nodes. Suggested fields:

| Field | Type | Description |
|-------|------|-------------|
| `keyword` | str | Input keyword |
| `keyword_analysis` | dict | Keyword Agent output |
| `brief` | dict | Content Brief Agent output |
| `content` | str | Article text (raw or optimized) |
| `quality_result` | dict | Quality Checker output |
| `is_duplicate` | bool | Duplicate Checker result |
| `duplicate_similarity` | float | Highest similarity to existing article |
| `seo_result` | dict | SEO Optimizer output |
| `article_id` | str/int | Article ID after save (if any) |
| `error` | str | Error message if any node fails |
| `current_node` | str | Current node name (for tracing) |

---

## 3. Conditional Edges

- **After duplicate_check:**
  - If `is_duplicate == True` → go to **reject** (or retry with different keyword per design).
  - If `is_duplicate == False` → go to **seo_optimizer**.

- **After quality_check (optional):**
  - If `quality_score` is below a threshold → either regenerate or continue with a warning (product decision).

---

## 4. Graph Definition File

| File | Responsibility |
|------|-----------------|
| `graphs/content_generation_graph.py` | Define State, add nodes, define edges (normal and conditional), build and export CompiledGraph |

---

## 5. Invoking the Graph from the Backend

- The backend (FastAPI) calls a function such as `run_content_generation(keyword, options)`.
- That function creates the graph (or uses a pre-built instance) and calls `graph.invoke(initial_state)`.
- The final result (including `article_id` or `error`) is returned to the API.

---

## 6. Error Handling

- Any node can set `error` in State and stop progress (final "failure" node).
- Retry can be implemented at the LLM-call level inside the agent or at the node level, depending on policy.
