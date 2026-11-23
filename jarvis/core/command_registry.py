from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from jarvis.core.intent_parser import Intent

LOGGER = logging.getLogger(__name__)


@dataclass()
class CommandResult:
    success: bool
    message: str


CommandHandler = Callable[[Intent], CommandResult]


class CommandRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, intent_name: str, handler: CommandHandler) -> None:
        key = intent_name.strip().upper()
        self._handlers[key] = handler

    def dispatch(self, intent: Intent) -> CommandResult:
        key = intent.name.strip().upper()
        handler = self._handlers.get(key)
        if handler is None:
            return CommandResult(success=False, message="I do not recognize that command yet.")

        try:
            return handler(intent)
        except Exception:
            LOGGER.exception("Command handler failed for intent=%s", key)
            return CommandResult(success=False, message="Internal command execution error.")
