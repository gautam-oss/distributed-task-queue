from enum import Enum


class Priority(str, Enum):
    HIGH = "high"
    DEFAULT = "default"
    LOW = "low"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class TaskType(str, Enum):
    SEND_EMAIL = "send_email"
    PROCESS_PAYMENT = "process_payment"
    GENERATE_REPORT = "generate_report"
    DATA_PIPELINE = "data_pipeline"
