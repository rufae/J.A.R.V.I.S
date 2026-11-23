from __future__ import annotations

import logging
import threading

from jarvis.core.state_manager import AssistantState, StateManager

LOGGER = logging.getLogger(__name__)


class WakeWordEngine:
    def __init__(self, state_manager: StateManager) -> None:
        self._state_manager = state_manager
        self._wake_event = threading.Event()

    def emit_wake_event(self) -> None:
        current_state = self._state_manager.state
        if current_state != AssistantState.IDLE:
            LOGGER.debug("Wake event ignored while in state %s", current_state.value)
            return
        self._wake_event.set()
        LOGGER.info("Wake event accepted")

    def wait_for_wake(self, timeout: float = 0.2) -> bool:
        triggered = self._wake_event.wait(timeout=timeout)
        if triggered:
            self._wake_event.clear()
        return triggered
