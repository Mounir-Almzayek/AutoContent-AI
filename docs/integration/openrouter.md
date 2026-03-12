# OpenRouter Integration and Token Tracking

## 1. OpenRouter as LLM Gateway

- **Purpose:** Call LLM models through a single API (OpenRouter).
- **Benefit:** Switch models (GPT-4, Claude, Mixtral, Llama, etc.) without code changes—only update the `model` setting.

---

## 2. Configuration

| Variable | Description |
|----------|-------------|
| OPENROUTER_API_KEY | API key from openrouter.ai |
| OPENROUTER_BASE_URL | Optional; default https://openrouter.ai/api/v1 |
| DEFAULT_MODEL | Default model (e.g. openai/gpt-4o or anthropic/claude-3-opus) |
| DEFAULT_TEMPERATURE | 0.0 – 2.0 |
| DEFAULT_MAX_TOKENS | Max output tokens |

---

## 3. OpenRouter Service (`services/openrouter_service.py`)

**Responsibilities:**

- Send Chat Completion requests to OpenRouter.
- Support parameters: `model`, `messages`, `temperature`, `max_tokens`.
- Read model from config or request override.
- Return text and (when available) usage from the response for token tracking.

**Suggested interface:**

- `chat(messages, model=None, temperature=None, max_tokens=None) -> (content: str, usage: dict)`
- `usage` contains: `prompt_tokens`, `completion_tokens`, `total_tokens` (and cost from OpenRouter if provided, passed to token_tracker).

---

## 4. Token Tracker (`services/token_tracker.py`)

**Responsibilities:**

- Record each call: `model`, `tokens_prompt`, `tokens_completion`, `total_tokens`, `cost`, `article_id` (optional), `timestamp`.
- Query functions:
  - By period (day, week, month).
  - By article (usage per article_id).
  - Total cost for a period.

Table schema is in [Data Models](../data/models.md) (`token_usage` table).

---

## 5. Supported Models (Examples)

A fixed list can be kept in the dashboard or fetched from OpenRouter:

- `openai/gpt-4o`
- `openai/gpt-4o-mini`
- `anthropic/claude-3-opus`
- `anthropic/claude-3-sonnet`
- `anthropic/claude-3-haiku`
- `mistralai/mixtral-8x7b-instruct`
- `meta-llama/llama-3-70b-instruct`

The user selects the model in the dashboard; it is stored in settings (DB or config), and the backend reads it for each OpenRouter call. Per-agent overrides are supported via `api/routes_settings` and `services/agent_settings`.
