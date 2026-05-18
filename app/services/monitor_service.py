import json
import logging
import os
import ssl

import redis

from ..celery_app.worker import celery_app
from ..models.task import DashboardStats

logger = logging.getLogger(__name__)

def _make_client(url: str) -> redis.Redis:
    kwargs: dict = {
        "decode_responses": True,
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
    }
    if url.startswith("rediss://"):
        kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
    return redis.from_url(url, **kwargs)

_broker_url  = os.getenv("CELERY_BROKER_URL",    "redis://localhost:6379/0")
# Note: Upstash free tier only supports db 0 — use the same URL for both
_backend_url = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

_broker_client  = _make_client(_broker_url)
_backend_client = _make_client(_backend_url)


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


def get_inspector_data() -> dict:
    """Full Celery inspect snapshot: active, reserved, scheduled tasks + worker stats."""
    try:
        insp = celery_app.control.inspect(timeout=3.0)
        active    = insp.active()    or {}
        reserved  = insp.reserved()  or {}
        scheduled = insp.scheduled() or {}
        stats     = insp.stats()     or {}

        workers = []
        for name in set(list(active) + list(stats)):
            s    = stats.get(name, {})
            pool = s.get("pool", {})
            total = s.get("total", {})
            processed = sum(total.values()) if isinstance(total, dict) else 0
            workers.append({
                "name":        name,
                "pid":         s.get("pid", "?"),
                "concurrency": pool.get("max-concurrency", "?"),
                "processed":   processed,
                "active":      len(active.get(name, [])),
                "reserved":    len(reserved.get(name, [])),
                "scheduled":   len(scheduled.get(name, [])),
            })

        # Flatten tasks with worker label
        def _tag(mapping: dict) -> list:
            out = []
            for worker_name, tasks in mapping.items():
                for t in (tasks or []):
                    out.append({**t, "worker": worker_name})
            return out

        return {
            "workers":   workers,
            "active":    _tag(active),
            "reserved":  _tag(reserved),
            "scheduled": _tag(scheduled),
        }
    except Exception:
        logger.warning("get_inspector_data failed", exc_info=True)
        return {"workers": [], "active": [], "reserved": [], "scheduled": []}
