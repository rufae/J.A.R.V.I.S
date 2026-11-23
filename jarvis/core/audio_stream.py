from __future__ import annotations

import contextlib
import logging
import math
import queue
import random
import threading
import time
from typing import Any

from jarvis.core.config import AudioConfig
from jarvis.core.state_manager import StateManager

LOGGER = logging.getLogger(__name__)


class AudioStreamService:
    def __init__(self, config: AudioConfig, state_manager: StateManager) -> None:
        self._config = config
        self._state_manager = state_manager
        self._amplitude_queue: queue.Queue[float] = queue.Queue(maxsize=200)
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream: Any | None = None

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()

        if not self._config.simulated_audio and self._start_sounddevice_stream():
            LOGGER.info("Audio stream started with sounddevice backend")
            return

        self._thread = threading.Thread(
            target=self._simulate_audio_loop, name="audio-sim", daemon=True
        )
        self._thread.start()
        LOGGER.warning("Audio stream running in simulated mode")

    def stop(self) -> None:
        self._running.clear()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                LOGGER.exception("Failed to stop audio stream")
            finally:
                self._stream = None

    def get_amplitude(self, timeout: float = 0.2) -> float | None:
        try:
            return self._amplitude_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _start_sounddevice_stream(self) -> bool:
        try:
            import sounddevice as sd
        except Exception:
            LOGGER.warning("sounddevice is not available")
            return False

        blocksize = int(self._config.sample_rate * self._config.block_duration_ms / 1000)

        def callback(indata: Any, _frames: int, _time_info: Any, status: Any) -> None:
            if status:
                LOGGER.debug("Audio callback status: %s", status)
            amplitude = self._rms(indata)
            self._push_amplitude(amplitude)

        try:
            self._stream = sd.InputStream(
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                blocksize=blocksize,
                callback=callback,
            )
            self._stream.start()
            return True
        except Exception:
            LOGGER.exception("Unable to start sounddevice input stream")
            return False

    def _simulate_audio_loop(self) -> None:
        period = max(self._config.block_duration_ms / 1000.0, 0.02)
        spike_chance = 0.03
        while self._running.is_set():
            base = random.uniform(0.01, 0.08)
            spike = random.uniform(0.55, 0.9) if random.random() < spike_chance else 0.0
            amplitude = min(1.0, base + spike)
            self._push_amplitude(amplitude)
            time.sleep(period)

    def _push_amplitude(self, amplitude: float) -> None:
        self._state_manager.set_mic_level(amplitude)
        try:
            self._amplitude_queue.put_nowait(amplitude)
        except queue.Full:
            with contextlib.suppress(queue.Empty):
                _ = self._amplitude_queue.get_nowait()
            self._amplitude_queue.put_nowait(amplitude)

    @staticmethod
    def _rms(samples: Any) -> float:
        try:
            values = samples.flatten().tolist()
        except Exception:
            try:
                values = list(samples)
            except Exception:
                return 0.0

        if not values:
            return 0.0

        power = sum(float(v) * float(v) for v in values) / len(values)
        return min(1.0, math.sqrt(power))
