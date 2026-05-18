import asyncio

from fastapi import APIRouter

from ...models.task import DashboardStats
from ...services.monitor_service import get_dashboard_stats, get_inspector_data, get_worker_count

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


@router.get("/inspect")
async def inspect_endpoint() -> dict:
    """
    Full Celery worker inspection snapshot.

    Returns per-worker metadata (hostname, PID, concurrency, processed count)
    plus flat lists of active, reserved, and scheduled tasks across all workers.

    - **active**    — tasks currently being executed by a worker process.
    - **reserved**  — tasks fetched from the broker but not yet started.
    - **scheduled** — tasks waiting for their ETA / countdown to expire.
    """
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, get_inspector_data),
            timeout=15.0,
        )
    except asyncio.TimeoutError:
        return {"workers": [], "active": [], "reserved": [], "scheduled": [], "error": "inspect timed out"}
