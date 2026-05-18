import traceback as tb

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...models.task import TaskRequest, TaskStatusResponse, TaskSubmitResponse
from ...services.task_service import cancel_task, get_task_status, submit_task

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/submit", response_model=TaskSubmitResponse, status_code=202)
async def submit_task_endpoint(request: TaskRequest):
    """
    Submit a background task for asynchronous execution.

    - **task_type**: One of `send_email`, `process_payment`, `generate_report`, `data_pipeline`.
    - **priority**: `high`, `default`, or `low` — determines which worker queue receives the task.
    - **payload**: Key/value arguments forwarded directly to the task function as `kwargs`.
      Must match the parameter names expected by the chosen task.
    - Returns immediately with a `task_id` and `PENDING` status.
      Poll `GET /tasks/{task_id}` to track progress.
    """
    try:
        return submit_task(
            task_type=request.task_type,
            priority=request.priority,
            payload=request.payload,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "traceback": tb.format_exc()},
        )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status_endpoint(task_id: str) -> TaskStatusResponse:
    """
    Retrieve the current status and result of a submitted task.

    Possible statuses:
    - **PENDING** — task has not yet been picked up by a worker (or the ID is unknown).
    - **STARTED** — a worker has begun executing the task (`task_track_started=True` required).
    - **RETRY** — the task failed and is waiting to be retried.
    - **SUCCESS** — the task completed successfully; `result` contains the return value.
    - **FAILURE** — the task raised an unhandled exception; `error` and `traceback` are populated.
    - **REVOKED** — the task was cancelled via `DELETE /tasks/{task_id}/cancel`.
    """
    return get_task_status(task_id)


@router.delete("/{task_id}/cancel")
async def cancel_task_endpoint(task_id: str) -> dict:
    """
    Cancel a queued or running task.

    Sends a revoke signal to all workers with `terminate=True`, which means:
    - If the task is still **queued**, it will be discarded and never executed.
    - If the task is **already running**, the worker process is sent SIGTERM and the task
      is interrupted immediately.

    Note: tasks that have already reached **SUCCESS** or **FAILURE** cannot be cancelled.
    """
    return cancel_task(task_id)
