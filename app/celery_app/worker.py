import os
from celery import Celery
from app.celery_app import celery_config

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "task_queue",
    broker=broker_url,
    backend=result_backend,
    include=["app.celery_app.tasks.sample_tasks"],
)

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
