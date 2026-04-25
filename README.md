# beanstalkpy

`beanstalkpy` is a high-performance, pure Python asyncio-based SDK for [beanstalkd](https://github.com/beanstalkd/beanstalkd). It provides a modern, asynchronous interface for interacting with the beanstalkd work queue, strictly adhering to the beanstalk protocol.

Gemini CLI work.

## Features
- **Pure Asyncio:** Built from the ground up for `asyncio`.
- **Full Protocol Support:** Implements every command described in the beanstalk protocol.
- **Connection Pooling:** Built-in pool manager for high-concurrency applications.
- **Strongly Typed:** Fully typed with Python type hints for better IDE support.
- **Zero Dependencies:** Requires only `PyYAML` for parsing server statistics.

## Installation

```bash
# From the project directory
pip install .
```

## Quick Start

### Producer Example

```python
import asyncio
from beanstalkpy import Client

async def producer():
    async with Client(host='127.0.0.1', port=11300) as client:
        # Switch to a specific tube
        await client.use('emails')
        
        # Put a job into the queue
        # priority=1024, delay=0, ttr=60
        job_id = await client.put(b"send welcome email to user@example.com")
        print(f"Job queued with ID: {job_id}")

asyncio.run(producer())
```

### Worker Example

```python
import asyncio
from beanstalkpy import Client

async def worker():
    async with Client() as client:
        # Watch specific tubes
        await client.watch('emails')
        await client.ignore('default')
        
        print("Waiting for jobs...")
        while True:
            # Reserve a job (blocks until one is available)
            job = await client.reserve()
            try:
                print(f"Processing job {job.id}: {job.body.decode()}")
                # Simulate work
                await asyncio.sleep(1)
                
                # Delete the job when finished
                await client.delete(job.id)
            except Exception as e:
                # Release it back to the queue if processing fails
                await client.release(job.id)
                print(f"Job {job.id} failed and was released: {e}")

asyncio.run(worker())
```

### Using the Connection Pool

```python
import asyncio
from beanstalkpy.pool import Pool

async def task(pool):
    async with pool.acquire() as client:
        await client.put(b"task data")

async def main():
    async with Pool(host='127.0.0.1', maxsize=10) as pool:
        tasks = [task(pool) for _ in range(20)]
        await asyncio.gather(*tasks)

asyncio.run(main())
```

## API Reference

The `Client` class implements the following beanstalkd protocol commands:

### Producer Commands
- `use(tube: str) -> str`: Specifies the tube to use for subsequent `put` commands.
- `put(body: bytes, priority: int, delay: int, ttr: int) -> int`: Puts a job into the currently used tube.

### Worker Commands
- `reserve(timeout: int = None) -> Job`: Reserves a job from the watch list.
- `reserve_job(job_id: int) -> Job`: Reserves a specific job by ID (beanstalkd 1.12+).
- `delete(job_id: int)`: Removes a job from the server entirely.
- `release(job_id: int, priority: int, delay: int)`: Puts a reserved job back into the ready queue.
- `bury(job_id: int, priority: int)`: Puts a job into the "buried" state.
- `touch(job_id: int)`: Requests more time to work on a reserved job.
- `watch(tube: str) -> int`: Adds a tube to the watch list.
- `ignore(tube: str) -> int`: Removes a tube from the watch list.

### Monitoring & Other Commands
- `peek(job_id: int) -> Job`: Inspects a specific job by ID.
- `peek_ready() -> Job`: Inspects the next ready job in the used tube.
- `peek_delayed() -> Job`: Inspects the delayed job with the shortest delay left.
- `peek_buried() -> Job`: Inspects the next buried job in the used tube.
- `kick(bound: int) -> int`: Moves jobs from buried/delayed to ready in the used tube.
- `kick_job(job_id: int)`: Kicks a specific job by ID.
- `stats_job(job_id: int) -> dict`: Returns statistics about a specific job.
- `stats_tube(tube: str) -> dict`: Returns statistics about a specific tube.
- `stats() -> dict`: Returns system-wide statistics.
- `list_tubes() -> list[str]`: Lists all existing tubes.
- `list_tube_used() -> str`: Returns the tube currently being used.
- `list_tubes_watched() -> list[str]`: Lists tubes currently being watched.
- `pause_tube(tube: str, delay: int)`: Delays new job reservations for a tube.
- `quit()`: Closes the connection.

## License
MIT
