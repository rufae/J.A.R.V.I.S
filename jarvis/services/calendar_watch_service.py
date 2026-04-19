from __future__ import annotations

import datetime as dt
import logging
import threading
import time
from typing import Callable

from jarvis.integrations.google_workspace import GoogleWorkspaceGateway


LOGGER = logging.getLogger(__name__)


class CalendarWatchService:
    def __init__(
        self,
        gateway: GoogleWorkspaceGateway,
        poll_seconds: int,
        reminder_window_minutes: int,
        on_reminder: Callable[[str], None],
    ) -> None:
        self._gateway = gateway
        self._poll_seconds = max(30, poll_seconds)
        self._reminder_window_minutes = max(1, reminder_window_minutes)
        self._on_reminder = on_reminder
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._notified_keys: set[str] = set()

    def start(self) -> None:
        if self._running.is_set() or not self._gateway.is_enabled():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._loop, name="calendar-watch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()

    def _loop(self) -> None:
        while self._running.is_set():
            self._poll_once()
            time.sleep(self._poll_seconds)

    def _poll_once(self) -> None:
        success, message, events = self._gateway.upcoming_events(max_results=10)
        if not success:
            LOGGER.debug("Calendar watch skipped: %s", message)
            return

        now = dt.datetime.utcnow()

        # Prune keys for events that have already passed to prevent unbounded growth.
        current_keys = {
            f"{event.get('summary','')}|{event.get('start','')}"
            for event in events
        }
        self._notified_keys &= current_keys

        for event in events:
            start = self._parse_datetime(event.get("start", ""))
            if start is None:
                continue
            delta_minutes = (start - now).total_seconds() / 60.0
            if delta_minutes < 0 or delta_minutes > self._reminder_window_minutes:
                continue

            key = f"{event.get('summary','')}|{event.get('start','')}"
            if key in self._notified_keys:
                continue

            reminder = f"Reminder: {event.get('summary', 'event')} starts at {event.get('start', '')}."
            self._notified_keys.add(key)
            self._on_reminder(reminder)

    @staticmethod
    def _parse_datetime(raw_value: str) -> dt.datetime | None:
        if not raw_value:
            return None
        normalized = raw_value.replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            return parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return parsed
