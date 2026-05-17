from fastapi import APIRouter

from ...models.task import DashboardStats
from ...services.monitor_service import get_dashboard_stats, get_worker_count

router = APIRouter(prefix="/workers", tags=["Workers"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats_endpoint() -> DashboardStats:
    """
    Return a live snapshot of queue depths, task state counts, and online worker count.
    """
    return get_dashboard_stats()


@router.get("/health")
async def health_endpoint() -> dict:
    """
    Lightweight liveness check that reports how many Celery workers are reachable.
    """
    count = get_worker_count()
    return {
        "workers_online": count,
        "status": "ok",
    }
