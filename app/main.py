import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .api.routes.tasks import router as tasks_router
from .api.routes.workers import router as workers_router
from .services.monitor_service import get_dashboard_stats, get_worker_count

app = FastAPI(
    title="Distributed Task Queue",
    description=(
        "Asynchronous task queue built with **Celery**, **Redis**, and **FastAPI**. "
        "Supports priority queues (high / default / low), real-time worker monitoring "
        "via WebSocket, and a live dashboard."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router, prefix="/api")
app.include_router(workers_router, prefix="/api")


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active = [c for c in self.active if c is not ws]

    async def broadcast(self, data: str) -> None:
        dead: list[WebSocket] = []
        for connection in self.active:
            try:
                await connection.send_text(data)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> HTMLResponse:
    html = Path(__file__).parent / "dashboard" / "index.html"
    return HTMLResponse(content=html.read_text(encoding="utf-8"))


@app.websocket("/ws/stats")
async def ws_stats(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        while True:
            # Run the blocking Redis + Celery inspect calls in a thread so
            # they never stall the event loop (which would break WS keepalive)
            loop = asyncio.get_event_loop()
            try:
                stats = await asyncio.wait_for(
                    loop.run_in_executor(None, get_dashboard_stats),
                    timeout=8.0,
                )
                await manager.broadcast(stats.model_dump_json())
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning("ws_stats error: %s", exc)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "Distributed Task Queue"}


@app.get("/debug/stats")
async def debug_stats() -> dict:
    import traceback as _tb
    import os as _os
    results: dict = {
        "broker_url": _os.getenv("CELERY_BROKER_URL", "NOT SET")[:40] + "...",
        "backend_url": _os.getenv("CELERY_RESULT_BACKEND", "NOT SET")[:40] + "...",
    }
    # Test broker ping
    try:
        from .services.monitor_service import _broker_client, _backend_client
        results["broker_ping"] = _broker_client.ping()
    except Exception as e:
        results["broker_ping"] = f"ERROR: {e}"
        results["broker_tb"] = _tb.format_exc()[-500:]
    # Test backend ping
    try:
        results["backend_ping"] = _backend_client.ping()
    except Exception as e:
        results["backend_ping"] = f"ERROR: {e}"
        results["backend_tb"] = _tb.format_exc()[-500:]
    # Test queue lengths
    try:
        from .services.monitor_service import get_queue_length
        results["queues"] = {
            "high": get_queue_length("high"),
            "default": get_queue_length("default"),
            "low": get_queue_length("low"),
        }
    except Exception as e:
        results["queues"] = f"ERROR: {e}"
    # Test worker count
    try:
        from .services.monitor_service import get_worker_count
        results["workers"] = get_worker_count()
    except Exception as e:
        results["workers"] = f"ERROR: {e}"
    return results
