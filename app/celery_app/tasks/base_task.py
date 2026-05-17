import logging
from celery import Task

logger = logging.getLogger(__name__)

_PRIORITY_TO_QUEUE = {
    "high": "high",
    "default": "default",
    "low": "low",
}


class BaseTaskWithRetry(Task):
    max_retries = 5
    default_retry_delay = 2

    def on_success(self, retval, task_id, args, kwargs):
        logger.info("[✅ SUCCESS] Task %s | ID: %s", self.name, task_id)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("[❌ FAILED] Task %s | ID: %s | Error: %s", self.name, task_id, exc)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning("[🔄 RETRY] Task %s | Retry #%d", self.name, self.request.retries)

    def apply_async_with_priority(self, args=None, kwargs=None, priority="default", **options):
        queue = _PRIORITY_TO_QUEUE.get(priority, "default")
        return self.apply_async(args=args, kwargs=kwargs, queue=queue, **options)
