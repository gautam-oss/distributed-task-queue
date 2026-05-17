import logging
import random
import time
import uuid

from ..worker import celery_app
from .base_task import BaseTaskWithRetry

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    base=BaseTaskWithRetry,
    name="app.celery_app.tasks.sample_tasks.send_email",
    max_retries=5,
)
def send_email(self, to: str, subject: str, body: str) -> dict:
    try:
        time.sleep(random.uniform(1, 3))
        if random.random() < 0.10:
            raise ConnectionError("SMTP connection refused")
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
            "message_id": str(uuid.uuid4()),
        }
    except ConnectionError as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(
    bind=True,
    base=BaseTaskWithRetry,
    name="app.celery_app.tasks.sample_tasks.process_payment",
    max_retries=3,
)
def process_payment(self, user_id: str, amount: float, currency: str = "USD") -> dict:
    try:
        time.sleep(random.uniform(2, 4))
        if random.random() < 0.20:
            raise ValueError(f"Payment gateway rejected transaction for user {user_id}")
        return {
            "status": "approved",
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "transaction_id": str(uuid.uuid4()),
        }
    except ValueError as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(
    bind=True,
    base=BaseTaskWithRetry,
    name="app.celery_app.tasks.sample_tasks.generate_report",
    max_retries=2,
)
def generate_report(self, report_type: str, user_id: str, date_range: str = "last_30_days") -> dict:
    try:
        stages = [
            "Fetching data",
            "Processing rows",
            "Rendering charts",
            "Exporting PDF",
        ]
        for stage in stages:
            logger.info("generate_report [%s] stage: %s", self.request.id, stage)
            time.sleep(random.uniform(2, 4))
        pages = random.randint(5, 40)
        return {
            "status": "completed",
            "report_type": report_type,
            "user_id": user_id,
            "file_url": f"/reports/{user_id}/{report_type}-{date_range}-{uuid.uuid4()}.pdf",
            "pages": pages,
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task(
    bind=True,
    base=BaseTaskWithRetry,
    name="app.celery_app.tasks.sample_tasks.data_pipeline",
    max_retries=2,
)
def data_pipeline(self, source: str, destination: str, record_count: int = 1000) -> dict:
    try:
        batch_size = 100
        records_processed = 0
        batches = (record_count + batch_size - 1) // batch_size
        for batch_num in range(batches):
            batch_end = min(records_processed + batch_size, record_count)
            logger.info(
                "data_pipeline [%s] batch %d/%d: records %d-%d",
                self.request.id,
                batch_num + 1,
                batches,
                records_processed + 1,
                batch_end,
            )
            time.sleep(random.uniform(1, 2))
            records_processed = batch_end
        return {
            "status": "completed",
            "source": source,
            "destination": destination,
            "records_processed": records_processed,
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
