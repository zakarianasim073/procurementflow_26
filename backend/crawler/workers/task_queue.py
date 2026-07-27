from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


class TaskPriority(Enum):
    HIGH = 0
    DEFAULT = 1
    LOW = 2


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class Task:
    priority: int
    created_at: float = field(compare=False)
    id: str = field(compare=False, default="")
    name: str = field(compare=False, default="")
    coro: Any = field(compare=False, default=None)
    kwargs: Dict[str, Any] = field(compare=False, default_factory=dict)
    status: TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    result: Any = field(compare=False, default=None)
    error: Optional[str] = field(compare=False, default=None)


class TaskQueue:
    def __init__(self, max_concurrent: int = 4):
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._sem = asyncio.Semaphore(max_concurrent)
        self._running: bool = False
        self._workers: List[asyncio.Task] = []
        self._results: Dict[str, Task] = {}
        self._max_concurrent = max_concurrent

    async def enqueue(
        self,
        name: str,
        coro: Callable,
        priority: TaskPriority = TaskPriority.DEFAULT,
        **kwargs,
    ) -> str:
        task_id = str(uuid4())[:12]
        task = Task(
            priority=priority.value,
            created_at=asyncio.get_event_loop().time(),
            id=task_id,
            name=name,
            coro=coro,
            kwargs=kwargs,
        )
        await self._queue.put(task)
        self._results[task_id] = task
        return task_id

    async def start(self, num_workers: Optional[int] = None):
        self._running = True
        num = num_workers or self._max_concurrent
        self._workers = [
            asyncio.create_task(self._worker_loop(f"worker-{i}"))
            for i in range(num)
        ]

    async def stop(self):
        self._running = False
        sentinel = Task(
            priority=0, created_at=0, id="_sentinel",
            name="_stop", coro=None,
        )
        for _ in range(len(self._workers)):
            await self._queue.put(sentinel)
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

    async def _worker_loop(self, name: str):
        while self._running:
            try:
                task = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                if task is None:
                    break
            except asyncio.TimeoutError:
                continue

            task.status = TaskStatus.RUNNING
            async with self._sem:
                try:
                    result = await task.coro(**task.kwargs)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED

    def get_result(self, task_id: str) -> Optional[Task]:
        return self._results.get(task_id)

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        return self._running
