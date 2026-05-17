# Distributed Task Queue

A production-style asynchronous task queue built with **Celery**, **Redis**, and **FastAPI** — featuring priority queues, automatic retries, and a real-time monitoring dashboard.

---

## Architecture

Here is how a task travels through the system, from the moment your code calls the API to the moment the result comes back:

```
                         ┌─────────────────────────────────────┐
                         │          WebSocket /ws/stats         │
                         │         (pushed every 2 sec)         │
                         └──────────────┬──────────────────────┘
                                        │
  ┌────────┐    HTTP POST    ┌──────────▼──────────┐
  │        │ ─────────────► │                     │
  │ Client │                │   FastAPI  :8000    │
  │        │ ◄───────────── │                     │
  └────────┘   task_id /    └──────────┬──────────┘
               result                  │
                               enqueue │ task
                                       ▼
                            ┌─────────────────────┐
                            │   Redis  :6379      │
                            │   (Celery Broker)   │
                            │                     │
                            │  queues:            │
                            │   • high   (db 0)   │
                            │   • default (db 0)  │
                            │   • low    (db 0)   │
                            └──────────┬──────────┘
                                       │ consume
                          ┌────────────┼────────────┐
                          ▼            ▼             ▼
                  ┌──────────────┐ ┌────────┐ ┌──────────┐
                  │ worker_high  │ │worker  │ │worker_low│
                  │ concurrency 4│ │default │ │concurr. 2│
                  │              │ │concurr.│ │          │
                  └──────┬───────┘ │   2    │ └────┬─────┘
                         │         └───┬────┘      │
                         └─────────────┼────────────┘
                                       │ store result
                                       ▼
                            ┌─────────────────────┐
                            │   Redis  :6379      │
                            │  (Result Backend)   │
                            │  task metadata      │
                            │  (db 1)             │
                            └──────────┬──────────┘
                                       │ AsyncResult.get()
                                       ▼
                            ┌─────────────────────┐
                            │   FastAPI  :8000    │
                            │  GET /tasks/{id}    │
                            └─────────────────────┘
```

**In plain English:** A client posts a task. FastAPI puts it on a Redis queue. One of the three Celery worker pools picks it up and runs it. The result is saved back to Redis. The client polls `GET /tasks/{id}` to see when it is done. Meanwhile, the dashboard receives a live feed of queue depths and worker counts over a WebSocket connection.

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Ports **8000**, **5555**, and **6379** free on your machine

### Start the stack

```bash
# Clone and enter the project
git clone <your-repo-url>
cd distributed-task-queue

# Build images and start all 6 services in the background
docker-compose up --build
```

The first build takes about 60–90 seconds while Docker downloads the base images and installs dependencies. Subsequent starts are fast.

### Open in your browser

| URL | What you will see |
|-----|-------------------|
| `http://localhost:8000` | Live monitoring dashboard |
| `http://localhost:8000/docs` | Interactive API docs (Swagger UI) |
| `http://localhost:5555` | Flower — Celery worker inspector |

---

## API Reference

All endpoints are prefixed with `/api`. The API returns JSON.

### Submit a task

Puts a task onto a queue and returns immediately. The task runs in the background.

```bash
curl -X POST http://localhost:8000/api/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "send_email",
    "priority": "high",
    "payload": {
      "to": "user@example.com",
      "subject": "Welcome!",
      "body": "Thanks for signing up."
    }
  }'
```

**Response `202 Accepted`:**
```json
{
  "task_id": "b3f1a2c4-8e7d-4f0a-9b6c-1d2e3f4a5b6c",
  "status": "PENDING",
  "priority": "high",
  "message": "Task 'send_email' queued on 'high' queue."
}
```

---

### Check task status

Poll this endpoint with the `task_id` you received at submission time.

```bash
curl http://localhost:8000/api/tasks/b3f1a2c4-8e7d-4f0a-9b6c-1d2e3f4a5b6c
```

**Response — task still running:**
```json
{
  "task_id": "b3f1a2c4-8e7d-4f0a-9b6c-1d2e3f4a5b6c",
  "status": "STARTED",
  "result": null,
  "error": null,
  "traceback": null
}
```

**Response — task complete:**
```json
{
  "task_id": "b3f1a2c4-8e7d-4f0a-9b6c-1d2e3f4a5b6c",
  "status": "SUCCESS",
  "result": {
    "status": "sent",
    "to": "user@example.com",
    "subject": "Welcome!",
    "message_id": "9f8e7d6c-5b4a-3c2d-1e0f-a1b2c3d4e5f6"
  },
  "error": null,
  "traceback": null
}
```

---

### Cancel a task

Sends a termination signal to all workers. If the task is queued, it is discarded. If it is running, the worker process is stopped immediately.

```bash
curl -X DELETE http://localhost:8000/api/tasks/b3f1a2c4-8e7d-4f0a-9b6c-1d2e3f4a5b6c/cancel
```

**Response:**
```json
{
  "task_id": "b3f1a2c4-8e7d-4f0a-9b6c-1d2e3f4a5b6c",
  "status": "revoked"
}
```

---

### Get dashboard stats

Returns live counts for queued tasks, task outcomes, and online workers.

```bash
curl http://localhost:8000/api/workers/stats
```

**Response:**
```json
{
  "queued_high": 3,
  "queued_default": 12,
  "queued_low": 0,
  "active_tasks": 5,
  "failed_tasks": 2,
  "success_tasks": 47,
  "workers_online": 3
}
```

---

## Demo Tasks

These four tasks are pre-built to simulate realistic workloads. Each can be submitted from the dashboard or directly via the API.

| Task | Queue | Simulated Duration | Failure Rate | What it simulates |
|------|-------|--------------------|--------------|-------------------|
| `send_email` | high | 1–3 seconds | 10% | SMTP network call |
| `process_payment` | high | 2–4 seconds | 20% | Payment gateway API |
| `generate_report` | low | 8–16 seconds | 0% | Multi-stage PDF export |
| `data_pipeline` | low | 10–20 seconds | 0% | Batch record processing |

### Payload reference

Use these exact JSON payloads in the `payload` field when calling `POST /api/tasks/submit`.

**send_email**
```json
{
  "to": "user@example.com",
  "subject": "Welcome aboard!",
  "body": "Thanks for signing up."
}
```

**process_payment**
```json
{
  "user_id": "usr_12345",
  "amount": 99.99,
  "currency": "USD"
}
```

**generate_report**
```json
{
  "report_type": "monthly_summary",
  "user_id": "usr_12345",
  "date_range": "last_30_days"
}
```

**data_pipeline**
```json
{
  "source": "s3://bucket/input",
  "destination": "s3://bucket/output",
  "record_count": 1000
}
```

---

## Retry Logic

When a task fails (raises an exception), Celery does not give up immediately. Instead it schedules a retry with a wait period that doubles after each attempt — this is called **exponential backoff**. It prevents a broken downstream service from being hammered with retries.

```
Attempt 1 fails  →  wait  2s  →  Attempt 2
Attempt 2 fails  →  wait  4s  →  Attempt 3
Attempt 3 fails  →  wait  8s  →  Attempt 4
Attempt 4 fails  →  wait 16s  →  Attempt 5
Attempt 5 fails  →  ✗ FAILURE (max_retries exceeded)
```

The wait between retries is calculated as `2 ** retries` seconds, where `retries` is the count of attempts that have already been made. Task-level retry limits:

| Task | `max_retries` | Max total wait before final failure |
|------|:-------------:|-------------------------------------|
| `send_email` | 5 | ~62 seconds |
| `process_payment` | 3 | ~14 seconds |
| `generate_report` | 2 | ~6 seconds |
| `data_pipeline` | 2 | ~6 seconds |

While a task is waiting between retries its status is shown as **RETRY** in the dashboard and API.

---

## Project Structure

```
distributed-task-queue/
│
├── docker-compose.yml          # Defines all 6 Docker services
├── Dockerfile                  # Builds the shared app image
├── requirements.txt            # Pinned Python dependencies
├── .env                        # Local dev environment variables
├── .env.example                # Template — copy this to create .env
├── .gitignore                  # Excludes venv, .env, __pycache__, etc.
│
└── app/
    ├── main.py                 # FastAPI app entry point, WebSocket, routes
    │
    ├── api/
    │   └── routes/
    │       ├── tasks.py        # POST /submit, GET /{id}, DELETE /{id}/cancel
    │       └── workers.py      # GET /stats, GET /health
    │
    ├── celery_app/
    │   ├── celery_config.py    # Queue definitions, routing, serialization settings
    │   ├── worker.py           # Celery app instance — reads broker/backend from env
    │   └── tasks/
    │       ├── base_task.py    # BaseTaskWithRetry — lifecycle hooks, priority helper
    │       └── sample_tasks.py # The 4 demo tasks with simulated work and failures
    │
    ├── models/
    │   ├── enums.py            # Priority, TaskStatus, TaskType enumerations
    │   └── task.py             # Pydantic request/response models
    │
    ├── services/
    │   ├── task_service.py     # submit_task, get_task_status, cancel_task
    │   └── monitor_service.py  # Queue lengths, dashboard stats, worker count
    │
    └── dashboard/
        └── index.html          # Single-file real-time monitoring UI
```

---

## Docker Services

| Service | Port | Role |
|---------|------|------|
| `redis` | 6379 | Message broker (queues) and result backend |
| `api` | 8000 | FastAPI — HTTP API and dashboard |
| `worker_high` | — | Celery worker — processes `high` queue only, concurrency 4 |
| `worker_default` | — | Celery worker — processes `default` queue only, concurrency 2 |
| `worker_low` | — | Celery worker — processes `low` queue only, concurrency 2 |
| `flower` | 5555 | Celery Flower — web UI for inspecting workers and tasks |

Workers have no exposed port because they only consume from Redis — they never receive incoming connections.

---

## Key Concepts Demonstrated

- **Priority Queues** — three separate queues (`high`, `default`, `low`) with dedicated worker pools, so a flood of low-priority background jobs can never delay an urgent payment or email.

- **Exponential Retry Backoff** — failed tasks are automatically retried with doubling wait times, preventing thundering-herd problems when a downstream service goes down briefly.

- **WebSocket Live Updates** — the dashboard opens a single persistent WebSocket connection and receives a stats snapshot every 2 seconds without any polling from the client side.

- **Result Backend** — completed task results (and errors) are stored in Redis so callers can retrieve them later via `GET /tasks/{id}`, decoupling the producer from the consumer.

- **Task Routing** — `celery_config.py` maps each task name to a specific queue, so developers do not need to specify the queue at the call site — the correct queue is chosen automatically.

- **Graceful Failure** — the `on_failure` lifecycle hook in `BaseTaskWithRetry` logs structured error information before giving up, making debugging straightforward without any changes to individual task code.
