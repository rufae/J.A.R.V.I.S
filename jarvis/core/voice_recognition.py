from __future__ import annotations

import audioop
import json
import logging
import re
import threading
import time
import wave
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from jarvis.core.config import VoiceConfig

LOGGER = logging.getLogger(__name__)


class VoiceRecognitionEngine:
    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._vosk_model: Any | None = None
        self._vosk_module: Any | None = None
        self._faster_whisper_model: Any | None = None
        self._prefetched_command = ""
        self._prefetch_lock = threading.Lock()
        self._init_vosk()
        self._init_faster_whisper()

    def consume_prefetched_command(self) -> str:
        with self._prefetch_lock:
            command = self._prefetched_command
            self._prefetched_command = ""
            return command

    def listen_for_command(self) -> str:
        backend = self._config.backend.strip().lower()

        if backend in {"faster-whisper", "auto"} and self._faster_whisper_model is not None:
            command = self._listen_with_faster_whisper()
            if command:
                LOGGER.info("Recognized command text: %s", command)
                return command

        if (
            backend in {"vosk", "auto"}
            and self._vosk_module is not None
            and self._vosk_model is not None
        ):
            command = self._listen_with_vosk()
            if command:
                LOGGER.info("Recognized command text: %s", command)
                return command

        command = ""
        if self._config.stdin_fallback:
            try:
                command = input("JARVIS command> ").strip().lower()
            except EOFError:
                command = ""

        if not command:
            command = self._config.demo_command.strip().lower()

        LOGGER.info("Recognized command text: %s", command)
        return command

    def wait_for_wake_phrase(self, stop_event: Any) -> bool:
        if self._faster_whisper_model is None:
            return False

        while not stop_event.is_set():
            text = self._listen_with_faster_whisper(
                max_duration=self._config.wake_max_listen_seconds,
                silence_timeout=min(self._config.silence_timeout_seconds, 1.2),
            )
            if not text:
                continue
            if self._matches_wake_phrase(text):
                command = self._extract_command_after_alias(text)
                if command:
                    with self._prefetch_lock:
                        self._prefetched_command = command
                LOGGER.info("Wake phrase detected: %s", text)
                return True

        return False

    def _init_vosk(self) -> None:
        if not self._config.vosk_model_path:
            return

        try:
            import vosk
        except Exception:
            LOGGER.warning("vosk package is not installed")
            return

        try:
            self._vosk_model = vosk.Model(self._config.vosk_model_path)
            self._vosk_module = vosk
            LOGGER.info("Loaded Vosk model from %s", self._config.vosk_model_path)
        except Exception:
            LOGGER.exception("Failed to load Vosk model")
            self._vosk_model = None
            self._vosk_module = None

    def _init_faster_whisper(self) -> None:
        if self._config.backend.strip().lower() not in {"faster-whisper", "auto"}:
            return

        try:
            from faster_whisper import WhisperModel
        except Exception:
            LOGGER.warning("faster-whisper is not available")
            return

        try:
            self._faster_whisper_model = WhisperModel(
                self._config.faster_whisper_model,
                device=self._config.faster_whisper_device,
                compute_type=self._config.faster_whisper_compute_type,
            )
            LOGGER.info(
                "Loaded faster-whisper model=%s device=%s compute_type=%s",
                self._config.faster_whisper_model,
                self._config.faster_whisper_device,
                self._config.faster_whisper_compute_type,
            )
        except Exception:
            LOGGER.exception("Failed to initialize faster-whisper")
            self._faster_whisper_model = None

    def _listen_with_vosk(self) -> str:
        try:
            import sounddevice as sd
        except Exception:
            LOGGER.warning("sounddevice is unavailable for Vosk listening")
            return ""

        sample_rate = 16_000
        block_duration_ms = 80
        block_size = int(sample_rate * block_duration_ms / 1000)
        recognizer = self._vosk_module.KaldiRecognizer(self._vosk_model, sample_rate)

        final_text = ""
        last_partial_at = time.time()
        start_at = time.time()

        try:
            with sd.RawInputStream(
                samplerate=sample_rate,
                blocksize=block_size,
                channels=1,
                dtype="int16",
            ) as stream:
                while True:
                    if time.time() - start_at > self._config.max_listen_seconds:
                        break

                    data, overflow = stream.read(block_size)
                    if overflow:
                        continue

                    if recognizer.AcceptWaveform(bytes(data)):
                        payload = json.loads(recognizer.Result())
                        text = payload.get("text", "").strip().lower()
                        if text:
                            final_text = text
                            break
                    else:
                        partial_payload = json.loads(recognizer.PartialResult())
                        partial = partial_payload.get("partial", "").strip().lower()
                        if partial:
                            last_partial_at = time.time()
                        elif time.time() - last_partial_at > self._config.silence_timeout_seconds:
                            break
        except Exception:
            LOGGER.exception("Vosk streaming recognition failed")
            return ""

        if final_text:
            return final_text

        try:
            payload = json.loads(recognizer.FinalResult())
            return payload.get("text", "").strip().lower()
        except Exception:
            return ""

    def _listen_with_faster_whisper(
        self,
        max_duration: float | None = None,
        silence_timeout: float | None = None,
    ) -> str:
        audio_path = self._record_utterance_to_wav(
            max_duration=max_duration,
            silence_timeout=silence_timeout,
        )
        if audio_path is None:
            return ""

        try:
            segments, _info = self._faster_whisper_model.transcribe(
                str(audio_path),
                vad_filter=self._config.vad_enabled,
                vad_parameters={
                    "min_silence_duration_ms": int(self._config.silence_timeout_seconds * 1000)
                },
                beam_size=1,
                language=self._config.asr_language or None,
            )
            return (
                " ".join(segment.text.strip() for segment in segments if segment.text.strip())
                .strip()
                .lower()
            )
        except Exception:
            LOGGER.exception("faster-whisper transcription failed")
            return ""
        finally:
            audio_path.unlink(missing_ok=True)

    def _record_utterance_to_wav(
        self,
        max_duration: float | None = None,
        silence_timeout: float | None = None,
    ) -> Path | None:
        try:
            import sounddevice as sd
        except Exception:
            LOGGER.warning("sounddevice is unavailable for faster-whisper listening")
            return None

        sample_rate = 16_000
        block_duration_ms = 100
        block_size = int(sample_rate * block_duration_ms / 1000)
        sample_width = 2
        silence_limit = (
            silence_timeout if silence_timeout is not None else self._config.silence_timeout_seconds
        )
        max_capture_duration = (
            max_duration if max_duration is not None else self._config.max_listen_seconds
        )
        speech_threshold = self._config.vad_speech_threshold

        frames: list[bytes] = []
        speech_started = False
        speech_started_at = 0.0
        last_speech_at = time.time()
        capture_started_at = time.time()

        try:
            with sd.RawInputStream(
                samplerate=sample_rate,
                blocksize=block_size,
                channels=1,
                dtype="int16",
            ) as stream:
                while True:
                    if time.time() - capture_started_at > max_capture_duration:
                        break

                    data, overflow = stream.read(block_size)
                    if overflow:
                        continue

                    chunk = bytes(data)
                    rms = audioop.rms(chunk, sample_width) / 32768.0
                    if rms >= speech_threshold:
                        if not speech_started:
                            speech_started = True
                            speech_started_at = time.time()
                        last_speech_at = time.time()

                    if speech_started:
                        frames.append(chunk)
                        if (
                            time.time() - last_speech_at > silence_limit
                            and time.time() - speech_started_at > 0.4
                        ):
                            break
        except Exception:
            LOGGER.exception("Audio capture for faster-whisper failed")
            return None

        if not frames:
            return None

        with NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            temp_path = Path(tmp_file.name)

        with wave.open(str(temp_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"".join(frames))

        return temp_path

    def _matches_wake_phrase(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        if not normalized:
            return False

        target = self._normalize_text(self._config.wake_phrase)
        aliases = [
            self._normalize_text(alias)
            for alias in self._config.wake_aliases.split(",")
            if alias.strip()
        ]

        # Accept exact wake phrase and phonetic alias variants like JARVIS/YARVIS.
        if target and target in normalized:
            return True

        contains_alias = any(alias and alias in normalized for alias in aliases)
        if not contains_alias:
            return False

        # Accept common wake variants if the alias is present.
        strong_markers = (
            "hola",
            "trabajar",
            "trabajemos",
            "activar",
            "activa",
            "despierta",
            "escucha",
        )
        if any(marker in normalized for marker in strong_markers):
            return True

        # Also allow direct "jarvis/yarvis + command" pattern.
        command_markers = ("abre", "open", "inicia", "lanza", "reproduce", "ejecuta")
        return any(marker in normalized for marker in command_markers)

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = text.strip().lower()
        replacements = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ü": "u",
        }
        for src, dst in replacements.items():
            lowered = lowered.replace(src, dst)
        lowered = re.sub(r"[^a-z0-9\s]", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()

    def _extract_command_after_alias(self, text: str) -> str:
        normalized = self._normalize_text(text)
        aliases = [
            self._normalize_text(alias)
            for alias in self._config.wake_aliases.split(",")
            if alias.strip()
        ]
        for alias in aliases:
            if not alias:
                continue
            match = re.search(rf"(?:^|\s){re.escape(alias)}\s+(?P<cmd>.+)$", normalized)
            if not match:
                continue
            cmd = match.group("cmd").strip()
            if cmd and cmd not in {"vamos a trabajar", "trabajar", "activa", "activar"}:
                return cmd
        return ""
