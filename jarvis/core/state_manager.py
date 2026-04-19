from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class AssistantState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    EXECUTING = "EXECUTING"
    SPEAKING = "SPEAKING"


@dataclass()
class StateSnapshot:
    state: AssistantState
    last_command: str
    last_response: str
    last_intent: str
    last_tool: str
    agent_mode: str
    active_task_id: str
    active_task_status: str
    mic_level: float
    timestamp: float


class StateManager:
    def __init__(self) -> None:
        self._state = AssistantState.IDLE
        self._last_command = ""
        self._last_response = ""
        self._last_intent = ""
        self._last_tool = ""
        self._agent_mode = "deterministic"
        self._active_task_id = ""
        self._active_task_status = ""
        self._mic_level = 0.0
        self._history: list[str] = []
        self._listeners: list[Callable[[StateSnapshot], None]] = []
        self._lock = threading.RLock()

    @property
    def state(self) -> AssistantState:
        with self._lock:
            return self._state

    def transition_to(self, next_state: AssistantState) -> None:
        with self._lock:
            self._state = next_state
            snapshot = self.snapshot_unlocked()
        self._notify(snapshot)

    def set_last_command(self, command: str) -> None:
        with self._lock:
            self._last_command = command
            self._history.append(f"CMD: {command}")
            snapshot = self.snapshot_unlocked()
        self._notify(snapshot)

    def set_last_response(self, response: str) -> None:
        with self._lock:
            self._last_response = response
            self._history.append(f"RSP: {response}")
            snapshot = self.snapshot_unlocked()
        self._notify(snapshot)

    def set_last_intent(self, intent_name: str) -> None:
        with self._lock:
            self._last_intent = intent_name
            self._history.append(f"INTENT: {intent_name}")
            snapshot = self.snapshot_unlocked()
        self._notify(snapshot)

    def set_last_tool(self, tool_name: str) -> None:
        with self._lock:
            self._last_tool = tool_name
            if tool_name:
                self._history.append(f"TOOL: {tool_name}")
            snapshot = self.snapshot_unlocked()
        self._notify(snapshot)

    def set_agent_mode(self, agent_mode: str) -> None:
        with self._lock:
            self._agent_mode = agent_mode
            snapshot = self.snapshot_unlocked()
        self._notify(snapshot)

    def add_history_entry(self, entry: str) -> None:
        with self._lock:
            self._history.append(entry)
            snapshot = self.snapshot_unlocked()
        self._notify(snapshot)

    def set_active_task(self, task_id: str, status: str) -> None:
        with self._lock:
            self._active_task_id = task_id
            self._active_task_status = status
            snapshot = self.snapshot_unlocked()
        self._notify(snapshot)

    def set_mic_level(self, level: float) -> None:
        with self._lock:
            self._mic_level = level
            snapshot = self.snapshot_unlocked()
        self._notify(snapshot)

    def history(self) -> list[str]:
        with self._lock:
            return list(self._history[-50:])

    def subscribe(self, listener: Callable[[StateSnapshot], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def snapshot(self) -> StateSnapshot:
        with self._lock:
            return self.snapshot_unlocked()

    def snapshot_unlocked(self) -> StateSnapshot:
        return StateSnapshot(
            state=self._state,
            last_command=self._last_command,
            last_response=self._last_response,
            last_intent=self._last_intent,
            last_tool=self._last_tool,
            agent_mode=self._agent_mode,
            active_task_id=self._active_task_id,
            active_task_status=self._active_task_status,
            mic_level=self._mic_level,
            timestamp=time.time(),
        )

    def _notify(self, snapshot: StateSnapshot) -> None:
        listeners = []
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            listener(snapshot)
