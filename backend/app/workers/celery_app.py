"""
QFlow Celery App — async task queue with priority routing.

Two queues:
  - fast: Short backtests (< 1 year), quick turnaround
  - slow: Multi-year or ML backtests, memory-intensive
"""

from celery import Celery
from kombu import Queue

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "qflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    # Queue definitions
    task_queues=(
        Queue("fast", routing_key="backtest.fast"),
        Queue("slow", routing_key="backtest.slow"),
    ),
    task_default_queue="fast",
    task_default_routing_key="backtest.fast",

    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Task tracking
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Timezone
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.workers"])
