#!/bin/sh
set -e

WORKER_TMP_DIR="${WORKER_TMP_DIR:-/dev/shm}"
if [ ! -d "$WORKER_TMP_DIR" ]; then
  WORKER_TMP_DIR=/tmp
fi

exec gunicorn \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads "${WEB_THREADS:-2}" \
  --timeout "${WEB_TIMEOUT:-120}" \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --worker-tmp-dir "$WORKER_TMP_DIR" \
  --access-logfile - \
  --error-logfile - \
  config.wsgi:application
