#!/bin/sh
# Ensure volume mount /data is writable by appuser (uid 1000)
if [ -d /data ]; then
  chown -R 1000:1000 /data 2>/dev/null || true
fi
# Run CMD as appuser (runuser on Debian; fallback to su)
if command -v runuser >/dev/null 2>&1; then
  exec runuser -u appuser -- "$@"
else
  exec su -s /bin/sh appuser -c 'exec "$@"' sh "$@"
fi
