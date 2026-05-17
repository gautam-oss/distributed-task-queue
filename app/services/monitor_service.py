import json
import logging
import os

import redis

from ..celery_app.worker import celery_app
from ..models.task import DashboardStats

logger = logging.getLogger(__name__)

_redis_host = os.getenv("REDIS_HOST", "localhost")
_redis_port = int(os.getenv("REDIS_PORT", 6379))

# db=0 — broker: holds queue lists
_broker_client = redis.Redis(
    host=_redis_host, port=_redis_port,
    db=int(os.getenv("REDIS_DB_BROKER", 0)),
    decode_responses=True,
)

# db=1 — backend: holds celery-task-meta-* result keys
_backend_client = redis.Redis(
    host=_redis_host, port=_redis_port,
    db=int(os.getenv("REDIS_DB_BACKEND", 1)),
    decode_responses=True,
)


def get_queue_length(queue_name: str) -> int:
    return _broker_client.llen(queue_name)


def get_dashboard_stats() -> DashboardStats:
    queued_high = get_queue_length("high")
    queued_default = get_queue_length("default")
    queued_low = get_queue_length("low")

    active_count = 0
    failed_count = 0
    success_count = 0

    cursor = 0
    while True:
        cursor, keys = _backend_client.scan(cursor, match="celery-task-meta-*", count=100)
        for key in keys:
            try:
                raw = _backend_client.get(key)
                if raw is None:
                    continue
                meta = json.loads(raw)
                state = meta.get("status", "")
                if state == "STARTED":
                    active_count += 1
                elif state == "FAILURE":
                    failed_count += 1
                elif state == "SUCCESS":
                    success_count += 1
            except (json.JSONDecodeError, TypeError):
                logger.warning("Could not parse task meta for key %s", key)
        if cursor == 0:
            break

    workers_online = get_worker_count()

    return DashboardStats(
        queued_high=queued_high,
        queued_default=queued_default,
        queued_low=queued_low,
        active_tasks=active_count,
        failed_tasks=failed_count,
        success_tasks=success_count,
        workers_online=workers_online,
    )


def get_worker_count() -> int:
    try:
        active = celery_app.control.inspect(timeout=1.0).active()
        if active is None:
            return 0
        return len(active)
    except Exception:
        logger.warning("Could not reach Celery workers for worker count", exc_info=True)
        return 0
