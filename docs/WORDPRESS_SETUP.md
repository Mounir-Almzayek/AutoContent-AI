# WordPress Setup — For the WordPress Team

This document explains **exactly what is required** on your WordPress site so that the AutoContent AI system can publish articles to it automatically.

---

## What the system does

AutoContent AI creates articles (title, content, excerpt) and **publishes them to your WordPress site** via the **WordPress REST API**. No direct access to your database or admin panel is used — only the public REST API with a secure application password.

---

## What you need to provide

The development/ops team will need **four values** from you. They will store these in the app configuration (not in the code):

| Value | Description | Example |
|-------|-------------|---------|
| **Site URL** | The full URL of the WordPress site (no trailing slash). Prefer **HTTPS**. | `https://yoursite.com` |
| **Username** | A WordPress user that can create and publish posts. | `editor1` or `autocontent` |
| **Application Password** | A dedicated app password (not the normal login password). See below. | `xxxx xxxx xxxx xxxx` |
| **Default post status** (optional) | How new posts should appear: `publish`, `draft`, or `private`. | `publish` or `draft` |

---

## 1. WordPress version and REST API

- **WordPress 4.7+** is required (REST API is built-in).
- The REST API is enabled by default at: `https://yoursite.com/wp-json/wp/v2/`
- If a security plugin or host has **disabled** the REST API or blocked external POST requests to `/wp-json/wp/v2/posts`, it must be **allowed** for the Application Password (or the IP/server that runs AutoContent AI), so that the app can create posts.

---

## 2. User account

- Create a **dedicated user** for the app (recommended), or use an existing one.
- The user **must** be able to **create and publish posts**:
  - **Administrator** — full access.
  - **Editor** — sufficient (can create, edit, publish posts).
- Do **not** use a user that can only contribute (e.g. Author) if you need immediate publishing; the app sends a “status” and the user must have the right capability.

---

## 3. Application Password (required)

We do **not** use the normal WordPress login password. We use an **Application Password**.

### How to create an Application Password

1. Log in to WordPress as an **Administrator**.
2. Go to **Users → Profile** (or **Users → All Users → edit the user** that will be used for the app).
3. Scroll to **Application Passwords**.
4. Enter a name (e.g. `AutoContent AI`) and click **Add New Application Password**.
5. WordPress will show a **one-time password** (e.g. `abcd efgh ijkl mnop qrst uvwx`). **Copy it immediately** and give it to the team — it cannot be viewed again.
6. The team will store it in the app config as `WORDPRESS_APP_PASSWORD` (spaces are allowed; the app uses it as-is).

**Security:**

- Application Passwords can be revoked from the same profile page.
- Use a dedicated WordPress user + one Application Password for this app, so you can revoke it without changing a human’s password.

---

## 4. What the app sends to WordPress

For each article, the app sends a **POST** request to:

`https://yoursite.com/wp-json/wp/v2/posts`

With:

- **title** — post title  
- **content** — post body (HTML)  
- **status** — `publish`, `draft`, or `private` (from your chosen default or configuration)  
- **excerpt** — if the article has a meta description, it is sent as excerpt (first 500 characters)

**Authentication:** `Authorization: Basic` with the username and Application Password (standard WordPress REST API auth).

Currently the app does **not** send categories or tags; those can be added later if you need them.

---

## 5. Checklist for the WordPress team

- [ ] WordPress 4.7 or newer.
- [ ] REST API available at `https://yoursite.com/wp-json/wp/v2/` (not blocked by plugin/host for the app).
- [ ] A user with **Editor** or **Administrator** role.
- [ ] An **Application Password** created for that user and shared securely with the dev/ops team.
- [ ] Site URL (no trailing slash), username, Application Password, and desired default status (`publish` / `draft` / `private`) communicated to the team for configuration.

---

## 6. What to give to the dev/ops team

Send them (via a secure channel):

1. **WORDPRESS_URL** — e.g. `https://yoursite.com`  
2. **WORDPRESS_USER** — the WordPress username  
3. **WORDPRESS_APP_PASSWORD** — the Application Password (with or without spaces; both work)  
4. **WORDPRESS_DEFAULT_STATUS** — `publish`, `draft`, or `private`  

They will add these to the app’s environment (e.g. `.env`) and will **not** store your normal WordPress login password.

---

## 7. If publishing fails

- **401 Unauthorized** — wrong username or Application Password, or Application Password revoked. Create a new one and update the config.
- **403 Forbidden** — user does not have permission to create/publish posts; use Editor or Administrator.
- **404** or **REST disabled** — REST API disabled or blocked; enable it or whitelist the app’s requests.
- **SSL / connection errors** — ensure the site URL uses HTTPS and the server can reach your WordPress site (no firewall blocking the app server).

If you have a security or caching plugin, ensure it does not block `POST /wp-json/wp/v2/posts` for requests that use the Application Password (or from the app’s IP).

---

*This setup is used by the AutoContent AI backend to publish articles to your WordPress site via the official REST API only.*
