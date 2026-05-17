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
            stats = get_dashboard_stats()
            payload = stats.model_dump_json()
            await manager.broadcast(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "Distributed Task Queue"}
