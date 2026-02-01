# Async and Sync Routes

## Core Principle

FastAPI is **async-first** but supports both async and sync routes. Understanding when to use each is critical for performance.

## Quick Decision Guide

| Operation Type                                               | Route Type                   | Example                                 |
| ------------------------------------------------------------ | ---------------------------- | --------------------------------------- |
| Non-blocking I/O (database, HTTP, file read with `aiofiles`) | `async def`                  | `await db.fetch()`, `await httpx.get()` |
| Blocking I/O (standard file ops, sync database drivers)      | `def`                        | `open().read()`, `requests.get()`       |
| CPU-intensive (data processing, calculations)                | Offload to worker            | Celery, multiprocessing                 |
| Async library available                                      | `async def`                  | Always prefer async when available      |
| Only sync library available                                  | `def` or `run_in_threadpool` | Isolate blocking code                   |

## Async Routes (`async def`)

### When to Use

- Database calls with async drivers (asyncpg, motor, etc.)
- HTTP requests with async libraries (httpx, aiohttp)
- File operations with aiofiles
- Any `await`-able operation
- Redis/cache operations with async drivers

### How It Works

```python
@router.get("/items")
async def get_items():
    # Non-blocking - event loop can handle other requests
    items = await db.fetch_all("SELECT * FROM items")
    return items
```

**Benefits:**

- Event loop continues processing other requests
- High concurrency with low resource usage
- Efficient I/O handling

**Critical Rule:** Only perform non-blocking operations in async routes!

### ❌ Wrong Usage - Blocking in Async Route

```python
import time

@router.get("/terrible-ping")
async def terrible_ping():
    time.sleep(10)  # BLOCKS THE ENTIRE EVENT LOOP! ❌
    return {"pong": True}
```

**Problem:** The `time.sleep(10)` blocks the entire event loop. No other requests can be processed during these 10 seconds. This negates all benefits of async.

**Impact:**

- Server becomes unresponsive
- All concurrent requests are blocked
- CPU sits idle but nothing gets processed

### ✅ Correct Usage - Non-blocking in Async Route

```python
import asyncio

@router.get("/perfect-ping")
async def perfect_ping():
    await asyncio.sleep(10)  # Non-blocking, event loop continues ✅
    return {"pong": True}
```

**Result:** During the 10-second sleep, the event loop can process thousands of other requests.

## Sync Routes (`def`)

### When to Use

- Standard library functions (most are blocking)
- Legacy sync libraries with no async alternative
- File operations without aiofiles
- CPU-bound operations (though worker queues are better)

### How It Works

```python
import time

@router.get("/good-ping")
def good_ping():
    time.sleep(10)  # Blocking, but runs in separate thread ✅
    return {"pong": True}
```

**FastAPI automatically runs sync routes in a threadpool.** The blocking operation doesn't block the event loop.

### Thread Pool Details

FastAPI uses Starlette's threadpool:

- Default thread count: typically 40 threads
- Each sync route runs in its own thread
- Event loop continues handling async operations

### ⚠️ Thread Pool Limitations

```python
# If you have 50 concurrent requests to this endpoint:
@router.get("/slow")
def slow_operation():
    time.sleep(5)  # Each takes 5 seconds
    return {"done": True}
```

**Problem:** Only 40 can run simultaneously (default thread limit). The other 10 wait.

**Solution:**

- Use async operations when possible
- Increase thread pool size if needed
- Offload heavy operations to worker queues

### Threads vs Coroutines

| Aspect               | Threads (sync routes) | Coroutines (async routes) |
| -------------------- | --------------------- | ------------------------- |
| Memory per operation | ~2-8 MB               | ~2-8 KB                   |
| Max concurrent       | ~Hundreds             | ~Tens of thousands        |
| Context switching    | OS-level (expensive)  | Event loop (cheap)        |
| Best for             | Blocking I/O          | Non-blocking I/O          |

## Mixing Async and Sync Code

### Using Sync Libraries in Async Routes

When you must use a sync library in an async route:

```python
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
import requests  # Sync HTTP library

app = FastAPI()

@router.get("/external-api")
async def call_external_api():
    # Run sync operation in threadpool
    response = await run_in_threadpool(
        requests.get,
        "https://api.example.com/data"
    )
    return response.json()
```

**When to use `run_in_threadpool`:**

- Sync library with no async alternative
- Legacy code that can't be refactored immediately
- Third-party SDKs that are sync-only

**Pattern for complex sync operations:**

```python
def complex_sync_operation(data: dict) -> dict:
    # Multiple sync operations
    result = sync_library.process(data)
    result = sync_library.transform(result)
    result = sync_library.validate(result)
    return result

@router.post("/process")
async def process_data(data: DataModel):
    result = await run_in_threadpool(complex_sync_operation, data.dict())
    return result
```

## CPU-Intensive Tasks

### ❌ Wrong - CPU Work in Routes

```python
@router.post("/process-video")
async def process_video(video: UploadFile):
    # This will block even with 'await' because it's CPU-bound ❌
    processed = await expensive_cpu_operation(video)
    return processed
```

**Problem:** CPU-bound work blocks a thread/coroutine regardless of async/sync.

### ✅ Correct - Offload to Workers

```python
from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379')

@celery_app.task
def process_video_task(video_path: str):
    # CPU-intensive work here
    return process_video(video_path)

@router.post("/process-video")
async def process_video(video: UploadFile):
    # Save file
    file_path = await save_file(video)

    # Queue task (non-blocking)
    task = process_video_task.delay(file_path)

    return {"task_id": task.id, "status": "processing"}

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    task = celery_app.AsyncResult(task_id)
    return {"status": task.status, "result": task.result}
```

**Options for CPU-intensive work:**

- **Celery**: Distributed task queue
- **multiprocessing**: For same-machine parallelism
- **Ray**: For ML/data processing workloads
- **External service**: Microservice dedicated to heavy computation

## Common Patterns

### Pattern 1: Async Database + Async HTTP

```python
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/user/{user_id}/external-data")
async def get_user_with_external_data(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Parallel execution
    user_task = db.execute(select(User).where(User.id == user_id))

    async with AsyncClient() as client:
        external_task = client.get(f"https://api.example.com/users/{user_id}")

    # Both complete concurrently
    user = (await user_task).scalar_one()
    external_data = (await external_task).json()

    return {"user": user, "external": external_data}
```

### Pattern 2: Gathering Multiple Async Operations

```python
import asyncio

@router.get("/dashboard")
async def get_dashboard(user_id: int):
    # Execute multiple async operations in parallel
    stats, posts, notifications = await asyncio.gather(
        get_user_stats(user_id),
        get_recent_posts(user_id),
        get_notifications(user_id)
    )

    return {
        "stats": stats,
        "posts": posts,
        "notifications": notifications
    }
```

### Pattern 3: Streaming Response (Async)

```python
from fastapi.responses import StreamingResponse

async def generate_data():
    for i in range(100):
        await asyncio.sleep(0.1)
        yield f"data: {i}\n\n"

@router.get("/stream")
async def stream_data():
    return StreamingResponse(generate_data(), media_type="text/event-stream")
```

## Python GIL (Global Interpreter Lock)

### Impact on Threads

The GIL means **only one thread executes Python bytecode at a time**:

✅ **Threads are effective for:**

- I/O-bound operations (waiting for network, disk, etc.)
- Operations that release the GIL (NumPy, some C extensions)

❌ **Threads are NOT effective for:**

- CPU-bound pure Python code
- Calculations, data processing, algorithms

### Why Async > Threads for I/O

```python
# 1000 concurrent I/O operations
# Threads: Need 1000 threads (8 GB memory)
# Async: One event loop (~8 MB memory)
```

Async coroutines are ~1000x lighter than threads.

## Performance Comparison

### Scenario: 1000 concurrent requests, each waits 1 second

**Async approach:**

```python
@router.get("/async-wait")
async def async_wait():
    await asyncio.sleep(1)
    return {"done": True}
```

- **Time:** ~1 second total
- **Memory:** ~10 MB
- **Can handle:** 100k+ concurrent requests

**Sync approach:**

```python
@router.get("/sync-wait")
def sync_wait():
    time.sleep(1)
    return {"done": True}
```

- **Time:** ~25 seconds (40 threads × 25 batches)
- **Memory:** ~300 MB (thread overhead)
- **Can handle:** ~40 concurrent requests

## Debugging Tips

### Check if Route is Async

```python
import inspect

print(inspect.iscoroutinefunction(my_route))  # True for async def
```

### Detect Blocking Calls in Async Code

Use `asyncio` debug mode:

```python
import asyncio

# In main.py
asyncio.get_event_loop().set_debug(True)
```

This warns when blocking operations take > 100ms in async context.

### Profiling Async Code

```python
import cProfile
import pstats

async def profile_this():
    pr = cProfile.Profile()
    pr.enable()

    await your_async_function()

    pr.disable()
    stats = pstats.Stats(pr)
    stats.sort_stats('cumulative')
    stats.print_stats()
```

## Summary: Decision Tree

```
Is the operation I/O-bound?
│
├─ YES: Does an async library exist?
│   │
│   ├─ YES: Use async def route → Best performance ✅
│   │
│   └─ NO: Can you use run_in_threadpool?
│       │
│       ├─ YES: Use async def + run_in_threadpool → Good
│       │
│       └─ NO: Use def route (sync) → Acceptable
│
└─ NO: Is it CPU-bound?
    │
    ├─ Light computation: def route → OK
    │
    └─ Heavy computation: Offload to Celery/worker → Required
```

## Key Takeaways

1. **Prefer async** when async libraries are available
2. **Never block** the event loop in async routes
3. **Use sync routes** for blocking operations (auto-threaded)
4. **Offload CPU work** to background workers
5. **Test under load** to verify async benefits
6. **Monitor thread pool** usage in production

## Common Mistakes Summary

| Mistake                         | Impact                  | Solution                        |
| ------------------------------- | ----------------------- | ------------------------------- |
| `time.sleep()` in `async def`   | Blocks event loop       | Use `await asyncio.sleep()`     |
| Heavy CPU work in route         | Blocks thread/coroutine | Use Celery/workers              |
| Using `requests` in `async def` | Unnecessary threading   | Use `httpx` (async)             |
| Too many sync routes            | Thread pool exhaustion  | Convert to async where possible |
| Mixing `await` with sync libs   | Still blocking          | Use `run_in_threadpool()`       |
