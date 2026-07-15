#!/bin/bash

# Start Celery worker in the background
celery -A app.workers.celery_app worker -Q fast,slow --concurrency=1 -l info &

# Start Uvicorn API server in the foreground
# Render automatically sets the PORT environment variable.
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
