# WordPress REST API Integration

## 1. Requirements

- WordPress site with REST API enabled (default in recent versions).
- User with "publish" capability (e.g. Editor or Administrator).
- Application password (Application Password) or Basic Auth with username and password.

---

## 2. Configuration

| Variable | Description |
|----------|-------------|
| WORDPRESS_URL | Site URL (e.g. https://example.com) |
| WORDPRESS_USER | Username |
| WORDPRESS_APP_PASSWORD | Application password |
| WORDPRESS_DEFAULT_STATUS | Post status: draft / publish / private |

---

## 3. Publish Endpoint

- **POST** `{WORDPRESS_URL}/wp-json/wp/v2/posts`

**Headers:**

- `Content-Type: application/json`
- `Authorization: Basic base64(user:app_password)`

**Body (minimal):**

```json
{
  "title": "Article title",
  "content": "HTML or block markup content",
  "status": "publish",
  "categories": [1, 2],
  "tags": [3, 4]
}
```

---

## 4. WordPress Service (`services/wordpress_service.py`)

**Responsibilities:**

- Build URL and headers from config.
- Function `publish_article(article_id)` or `publish_article(title, content, meta_title, meta_description, categories, tags)`:
  - Send POST to `/wp/v2/posts`.
  - On success: store `wordpress_id` and `published_at` on the article.
  - On failure: set article `status` to failed and store `error_message`.

- (Optional) Later: update post (PUT), delete, or GET categories/tags for use in the dashboard.

---

## 5. Categories and Tags

- Categories: GET `{WORDPRESS_URL}/wp-json/wp/v2/categories`.
- Tags: GET `{WORDPRESS_URL}/wp-json/wp/v2/tags`.
- Optional: add fields on articles or in settings for `default_category_id`, `default_tag_ids` to use when publishing if the user does not specify them.
