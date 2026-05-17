#!/bin/bash
set -e

echo "Starting Celery worker..."
celery -A app.celery_app.worker.celery_app worker \
  --queues=high,default,low \
  --concurrency=2 \
  --loglevel=info &

echo "Starting FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
