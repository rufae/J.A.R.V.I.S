from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from typing import Callable

from jarvis.agent.memory_store import AgentMemoryStore
from jarvis.agent.memory_store import TASK_STATUS_COMPLETED
from jarvis.agent.memory_store import TASK_STATUS_FAILED
from jarvis.agent.memory_store import TASK_STATUS_PENDING
from jarvis.agent.memory_store import TASK_STATUS_RUNNING
from jarvis.agent.models import AgentExecutionResult


LOGGER = logging.getLogger(__name__)


@dataclass()
class QueuedTask:
    task_id: str
    goal: str
    source: str


class TaskExecutionEngine:
    def __init__(
        self,
        memory_store: AgentMemoryStore,
        executor: Callable[[str], AgentExecutionResult],
        max_attempts: int,
        retry_delay_seconds: int,
        on_task_update: Callable[[str], None] | None = None,
    ) -> None:
        self._memory_store = memory_store
        self._executor = executor
        self._max_attempts = max(1, max_attempts)
        self._retry_delay_seconds = max(1, retry_delay_seconds)
        self._on_task_update = on_task_update
        self._queue: queue.Queue[QueuedTask] = queue.Queue()
        self._running = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._worker, name="task-engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()

    def submit(self, goal: str, source: str = "voice") -> str:
        task_id = self._memory_store.create_task(goal=goal, source=source)
        self._queue.put(QueuedTask(task_id=task_id, goal=goal, source=source))
        self._emit_update(task_id)
        return task_id

    def recent_tasks(self, limit: int = 10) -> list[dict[str, str]]:
        return self._memory_store.recent_tasks(limit=limit)

    def get_task(self, task_id: str) -> dict[str, str] | None:
        return self._memory_store.get_task(task_id)

    def _worker(self) -> None:
        while self._running.is_set():
            try:
                queued_task = self._queue.get(timeout=0.3)
            except queue.Empty:
                continue

            self._execute_task(queued_task)

    def _execute_task(self, queued_task: QueuedTask) -> None:
        attempts = 0
        last_error = ""

        while self._running.is_set() and attempts < self._max_attempts:
            attempts += 1
            self._memory_store.update_task(
                task_id=queued_task.task_id,
                status=TASK_STATUS_RUNNING,
                attempts=attempts,
            )
            self._emit_update(queued_task.task_id)

            try:
                result = self._executor(queued_task.goal)
            except Exception:
                LOGGER.exception("Task execution crashed for %s", queued_task.task_id)
                result = AgentExecutionResult(success=False, response="Task execution crashed.")

            if result.success:
                self._memory_store.update_task(
                    task_id=queued_task.task_id,
                    status=TASK_STATUS_COMPLETED,
                    attempts=attempts,
                    result_text=result.response,
                )
                self._emit_update(queued_task.task_id)
                return

            last_error = result.response
            if attempts < self._max_attempts:
                self._memory_store.update_task(
                    task_id=queued_task.task_id,
                    status=TASK_STATUS_PENDING,
                    attempts=attempts,
                    last_error=last_error,
                )
                self._emit_update(queued_task.task_id)
                time.sleep(self._retry_delay_seconds)

        self._memory_store.update_task(
            task_id=queued_task.task_id,
            status=TASK_STATUS_FAILED,
            attempts=attempts,
            last_error=last_error,
            result_text=last_error,
        )
        self._emit_update(queued_task.task_id)

    def _emit_update(self, task_id: str) -> None:
        if self._on_task_update is not None:
            self._on_task_update(task_id)
