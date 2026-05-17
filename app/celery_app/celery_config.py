from kombu import Queue

CELERY_QUEUES = (
    Queue("high"),
    Queue("default"),
    Queue("low"),
)

CELERY_DEFAULT_QUEUE = "default"

CELERY_TASK_ROUTES = {
    "app.celery_app.tasks.sample_tasks.send_email":      {"queue": "high"},
    "app.celery_app.tasks.sample_tasks.process_payment": {"queue": "high"},
    "app.celery_app.tasks.sample_tasks.generate_report": {"queue": "low"},
    "app.celery_app.tasks.sample_tasks.data_pipeline":   {"queue": "low"},
}

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

CELERY_TASK_TRACK_STARTED = True
CELERY_RESULT_EXPIRES = 3600
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
