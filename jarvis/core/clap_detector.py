from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from jarvis.core.audio_stream import AudioStreamService
from jarvis.core.config import AudioConfig

LOGGER = logging.getLogger(__name__)


class ClapDetectorService:
    def __init__(
        self,
        audio_stream: AudioStreamService,
        config: AudioConfig,
        on_wake_event: Callable[[], None],
    ) -> None:
        self._audio_stream = audio_stream
        self._config = config
        self._on_wake_event = on_wake_event
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._clap_times: list[float] = []
        self._last_clap_time = 0.0

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._run_loop, name="clap-detector", daemon=True)
        self._thread.start()
        LOGGER.info("Clap detector service started")

    def stop(self) -> None:
        self._running.clear()

    def _run_loop(self) -> None:
        min_gap = self._config.min_clap_gap_ms / 1000.0
        window = self._config.clap_window_seconds
        threshold = self._config.clap_threshold

        while self._running.is_set():
            amplitude = self._audio_stream.get_amplitude(timeout=0.2)
            if amplitude is None:
                continue

            now = time.time()
            if amplitude >= threshold and (now - self._last_clap_time) > min_gap:
                self._last_clap_time = now
                self._clap_times.append(now)
                LOGGER.debug("Clap candidate detected amplitude=%.3f", amplitude)

            self._clap_times = [t for t in self._clap_times if (now - t) <= window]
            if (
                len(self._clap_times) == 2
                and (self._clap_times[-1] - self._clap_times[0]) <= window
            ):
                LOGGER.info("Wake event detected by double clap")
                self._clap_times.clear()
                self._on_wake_event()
            elif len(self._clap_times) > 2:
                self._clap_times = self._clap_times[-2:]
