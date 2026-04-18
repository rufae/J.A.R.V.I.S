from __future__ import annotations

import threading
from typing import Any

from jarvis.core.state_manager import StateManager


class UIStateBridge:
    def __init__(self, state_manager: StateManager) -> None:
        self._state_manager = state_manager
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {
            "state": "IDLE",
            "last_command": "",
            "last_response": "",
            "last_intent": "",
            "last_tool": "",
            "agent_mode": "deterministic",
            "active_task_id": "",
            "active_task_status": "",
            "mic_level": 0.0,
            "history": [],
        }

        self._state_manager.subscribe(self._on_state_update)

    def _on_state_update(self, snapshot: Any) -> None:
        with self._lock:
            self._data = {
                "state": snapshot.state.value,
                "last_command": snapshot.last_command,
                "last_response": snapshot.last_response,
                "last_intent": snapshot.last_intent,
                "last_tool": snapshot.last_tool,
                "agent_mode": snapshot.agent_mode,
                "active_task_id": snapshot.active_task_id,
                "active_task_status": snapshot.active_task_status,
                "mic_level": round(snapshot.mic_level, 4),
                "history": self._state_manager.history(),
            }

    def current_state(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)
