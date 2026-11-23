from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path

TASK_STATUS_PENDING = "PENDING"
TASK_STATUS_RUNNING = "RUNNING"
TASK_STATUS_COMPLETED = "COMPLETED"
TASK_STATUS_FAILED = "FAILED"


class AgentMemoryStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path.expanduser().resolve()
        self._lock = threading.Lock()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def record_interaction(
        self,
        user_text: str,
        response_text: str,
        intent_name: str,
        tool_name: str,
        agent_mode: str,
    ) -> None:
        with self._lock, sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO interactions
                    (created_at, user_text, response_text, intent_name, tool_name, agent_mode)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    time.time(),
                    user_text,
                    response_text,
                    intent_name,
                    tool_name,
                    agent_mode,
                ),
            )
            connection.commit()

    def recent_interactions(self, limit: int = 8) -> list[dict[str, str]]:
        with self._lock, sqlite3.connect(self._database_path) as connection:
            cursor = connection.execute(
                """
                SELECT user_text, response_text, intent_name, tool_name, agent_mode
                FROM interactions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        interactions = []
        for row in rows:
            interactions.append(
                {
                    "user_text": str(row[0] or ""),
                    "response_text": str(row[1] or ""),
                    "intent_name": str(row[2] or ""),
                    "tool_name": str(row[3] or ""),
                    "agent_mode": str(row[4] or ""),
                }
            )
        return interactions

    def create_task(self, goal: str, source: str) -> str:
        task_id = str(uuid.uuid4())
        with self._lock, sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                INSERT INTO tasks
                    (task_id, created_at, updated_at, goal, status, source, attempts,
                     last_error, result_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    time.time(),
                    time.time(),
                    goal,
                    TASK_STATUS_PENDING,
                    source,
                    0,
                    "",
                    "",
                ),
            )
            connection.commit()
        return task_id

    def update_task(
        self,
        task_id: str,
        status: str,
        attempts: int,
        last_error: str = "",
        result_text: str = "",
    ) -> None:
        with self._lock, sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                UPDATE tasks
                SET updated_at = ?, status = ?, attempts = ?, last_error = ?, result_text = ?
                WHERE task_id = ?
                """,
                (time.time(), status, attempts, last_error, result_text, task_id),
            )
            connection.commit()

    def get_task(self, task_id: str) -> dict[str, str] | None:
        with self._lock, sqlite3.connect(self._database_path) as connection:
            cursor = connection.execute(
                """
                SELECT task_id, goal, status, source, attempts, last_error, result_text
                FROM tasks
                WHERE task_id = ?
                """,
                (task_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "task_id": str(row[0]),
            "goal": str(row[1]),
            "status": str(row[2]),
            "source": str(row[3]),
            "attempts": str(row[4]),
            "last_error": str(row[5] or ""),
            "result_text": str(row[6] or ""),
        }

    def recent_tasks(self, limit: int = 10) -> list[dict[str, str]]:
        with self._lock, sqlite3.connect(self._database_path) as connection:
            cursor = connection.execute(
                """
                SELECT task_id, goal, status, source, attempts, last_error, result_text
                FROM tasks
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
        tasks = []
        for row in rows:
            tasks.append(
                {
                    "task_id": str(row[0]),
                    "goal": str(row[1]),
                    "status": str(row[2]),
                    "source": str(row[3]),
                    "attempts": str(row[4]),
                    "last_error": str(row[5] or ""),
                    "result_text": str(row[6] or ""),
                }
            )
        return tasks

    def _initialize(self) -> None:
        with self._lock, sqlite3.connect(self._database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    user_text TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    intent_name TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    agent_mode TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    last_error TEXT NOT NULL,
                    result_text TEXT NOT NULL
                )
                """
            )
            connection.commit()
