# Nginx reverse proxy (two domains)

Use **one domain for the API** and **one for the Dashboard** so traffic goes through nginx and is proxied to the correct port (no direct port exposure).

1. Copy `autocontent-ai.conf.example` to your nginx config (e.g. `/etc/nginx/sites-available/autocontent-ai`).
2. Replace `api.yourdomain.com` and `dashboard.yourdomain.com` with your real domains.
3. If nginx runs on a **different host** than Docker, change `127.0.0.1` to the IP/host of the machine where the containers run (ports 8000 and 8501).
4. Enable the site and reload nginx:
   ```bash
   sudo ln -s /etc/nginx/sites-available/autocontent-ai /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
5. Point both DNS A records to the nginx server. Optionally use certbot for HTTPS.

Containers and volumes use unique names (`autocontent_ai_*`) so they do not conflict with other projects on the same host.
