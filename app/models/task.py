from typing import Any, Optional

from pydantic import BaseModel

from .enums import Priority, TaskStatus, TaskType


class TaskRequest(BaseModel):
    task_type: TaskType
    priority: Priority = Priority.DEFAULT
    payload: dict[str, Any] = {}

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_type": "send_email",
                "priority": "high",
                "payload": {
                    "to": "user@example.com",
                    "subject": "Welcome aboard!",
                    "body": "Thanks for signing up.",
                },
            }
        }
    }


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: TaskStatus
    priority: Priority
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    traceback: Optional[str] = None


class DashboardStats(BaseModel):
    queued_high: int
    queued_default: int
    queued_low: int
    active_tasks: int
    failed_tasks: int
    success_tasks: int
    workers_online: int
