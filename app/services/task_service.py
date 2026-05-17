import logging
from celery.result import AsyncResult

from ..celery_app.worker import celery_app
from ..celery_app.tasks.sample_tasks import (
    data_pipeline,
    generate_report,
    process_payment,
    send_email,
)
from ..models.enums import Priority, TaskStatus, TaskType
from ..models.task import TaskStatusResponse, TaskSubmitResponse

logger = logging.getLogger(__name__)

TASK_MAP = {
    TaskType.SEND_EMAIL: send_email,
    TaskType.PROCESS_PAYMENT: process_payment,
    TaskType.GENERATE_REPORT: generate_report,
    TaskType.DATA_PIPELINE: data_pipeline,
}


def submit_task(task_type: TaskType, priority: Priority, payload: dict) -> TaskSubmitResponse:
    task_fn = TASK_MAP[task_type]
    result = task_fn.apply_async(kwargs=payload, queue=priority.value)
    logger.info("Submitted task %s [%s] → queue=%s", task_type.value, result.id, priority.value)
    return TaskSubmitResponse(
        task_id=result.id,
        status=TaskStatus.PENDING,
        priority=priority,
        message=f"Task '{task_type.value}' queued on '{priority.value}' queue.",
    )


def get_task_status(task_id: str) -> TaskStatusResponse:
    result = AsyncResult(task_id, app=celery_app)
    raw_state = result.state

    try:
        status = TaskStatus(raw_state)
    except ValueError:
        status = TaskStatus.PENDING

    task_result = None
    error = None
    traceback = None

    if status == TaskStatus.SUCCESS:
        task_result = result.result
    elif status == TaskStatus.FAILURE:
        error = str(result.result)
        traceback = result.traceback

    return TaskStatusResponse(
        task_id=task_id,
        status=status,
        result=task_result,
        error=error,
        traceback=traceback,
    )


def cancel_task(task_id: str) -> dict:
    celery_app.control.revoke(task_id, terminate=True)
    logger.info("Revoked task %s", task_id)
    return {"task_id": task_id, "status": "revoked"}
