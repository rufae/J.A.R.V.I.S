from __future__ import annotations

import logging
import queue
import re
import subprocess
import threading
import wave
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import sounddevice as sd

from jarvis.core.config import TTSConfig


LOGGER = logging.getLogger(__name__)


class SpeechEngine:
    def __init__(self, config: TTSConfig) -> None:
        self._config = config
        self._messages: queue.Queue[str] = queue.Queue(maxsize=100)
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._engine = None
        self._backend = "disabled"

    def start(self) -> None:
        if not self._config.enabled or self._running.is_set():
            return
        self._running.set()
        self._init_engine()
        self._thread = threading.Thread(target=self._worker, name="tts-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()

    def speak(self, text: str) -> None:
        if not text:
            return
        if not self._config.enabled:
            LOGGER.info("TTS disabled, response text: %s", text)
            return
        try:
            self._messages.put_nowait(text)
        except queue.Full:
            LOGGER.warning("TTS queue is full, dropping message")

    def _init_engine(self) -> None:
        backend = self._config.backend.strip().lower()
        if backend == "kokoro" and self._init_kokoro():
            self._backend = "kokoro"
            return
        if backend == "piper" and self._init_piper():
            self._backend = "piper"
            return
        if self._init_pyttsx3():
            self._backend = "pyttsx3"
            return
        LOGGER.warning("No TTS backend available, speech will be text-only")
        self._backend = "text"

    def _worker(self) -> None:
        while self._running.is_set():
            try:
                text = self._messages.get(timeout=0.2)
            except queue.Empty:
                continue

            if self._backend == "text" or self._engine is None:
                LOGGER.info("TTS message: %s", text)
                continue

            try:
                for chunk in self._iter_chunks(text):
                    self._speak_chunk(chunk)
            except Exception:
                LOGGER.exception("TTS engine failed for message")

    def _init_kokoro(self) -> bool:
        try:
            from kokoro import KPipeline
        except Exception:
            LOGGER.warning("kokoro is not available")
            return False

        try:
            self._engine = KPipeline(lang_code=self._config.kokoro_lang_code)
            return True
        except Exception:
            LOGGER.exception("Failed to initialize Kokoro TTS")
            self._engine = None
            return False

    def _init_piper(self) -> bool:
        model_path = self._config.piper_model_path.strip()
        if not model_path:
            LOGGER.warning("Piper backend selected but no model path configured")
            return False
        self._engine = {"binary": self._config.piper_binary, "model_path": model_path}
        return True

    def _init_pyttsx3(self) -> bool:
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", self._config.rate)
            engine.setProperty("volume", self._config.volume)
            self._engine = engine
            return True
        except Exception:
            LOGGER.warning("pyttsx3 is not available")
            self._engine = None
            return False

    def _iter_chunks(self, text: str) -> list[str]:
        normalized = text.strip()
        if not normalized:
            return []
        if not self._config.stream_sentences:
            return [normalized]
        chunks = [item.strip() for item in re.split(r"(?<=[.!?])\s+", normalized) if item.strip()]
        return chunks or [normalized]

    def _speak_chunk(self, text: str) -> None:
        if self._backend == "kokoro":
            self._speak_kokoro(text)
            return
        if self._backend == "piper":
            self._speak_piper(text)
            return
        self._engine.say(text)
        self._engine.runAndWait()

    def _speak_kokoro(self, text: str) -> None:
        generator = self._engine(
            text,
            voice=self._config.kokoro_voice,
            speed=1,
            split_pattern=r"\n+",
        )
        for _index, (_graphemes, _phonemes, audio) in enumerate(generator):
            sd.play(audio, 24000)
            sd.wait()

    def _speak_piper(self, text: str) -> None:
        engine = self._engine
        with NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            temp_path = Path(tmp_file.name)
        try:
            command = [
                engine["binary"],
                "--model",
                engine["model_path"],
                "--output_file",
                str(temp_path),
            ]
            process = subprocess.run(
                command,
                input=text,
                text=True,
                check=False,
                capture_output=True,
                timeout=60,
            )
            if process.returncode != 0:
                raise RuntimeError(process.stderr.strip() or "Piper synthesis failed")
            self._play_wav_file(temp_path)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    @staticmethod
    def _play_wav_file(path: Path) -> None:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            samplerate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()

        dtype = np.int16 if sample_width == 2 else np.uint8
        playback = np.frombuffer(frames, dtype=dtype)
        if channels > 1:
            playback = playback.reshape(-1, channels)
        sd.play(playback, samplerate=samplerate)
        sd.wait()
