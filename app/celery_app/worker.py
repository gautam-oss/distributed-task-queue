import os
import ssl
from celery import Celery
from app.celery_app import celery_config

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
# Note: Upstash free tier only supports db 0 — both broker and backend use db 0
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "task_queue",
    broker=broker_url,
    backend=result_backend,
    include=["app.celery_app.tasks.sample_tasks"],
)

# Enable SSL for Upstash/TLS Redis connections (rediss://)
if broker_url.startswith("rediss://"):
    _ssl = {"ssl_cert_reqs": ssl.CERT_NONE}
    celery_app.conf.broker_use_ssl = _ssl
    celery_app.conf.redis_backend_use_ssl = _ssl

celery_app.conf.update(
    task_queues=celery_config.CELERY_QUEUES,
    task_default_queue=celery_config.CELERY_DEFAULT_QUEUE,
    task_routes=celery_config.CELERY_TASK_ROUTES,
    task_serializer=celery_config.CELERY_TASK_SERIALIZER,
    result_serializer=celery_config.CELERY_RESULT_SERIALIZER,
    accept_content=celery_config.CELERY_ACCEPT_CONTENT,
    task_track_started=celery_config.CELERY_TASK_TRACK_STARTED,
    result_expires=celery_config.CELERY_RESULT_EXPIRES,
    worker_prefetch_multiplier=celery_config.CELERY_WORKER_PREFETCH_MULTIPLIER,
    task_acks_late=celery_config.CELERY_TASK_ACKS_LATE,
)
