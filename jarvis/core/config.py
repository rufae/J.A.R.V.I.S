from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass()
class AudioConfig:
    sample_rate: int = 16_000
    channels: int = 1
    block_duration_ms: int = 30
    clap_threshold: float = 0.35
    clap_window_seconds: float = 1.5
    min_clap_gap_ms: int = 150
    simulated_audio: bool = False


@dataclass()
class VoiceConfig:
    backend: str = "vosk"
    vosk_model_path: str = ""
    faster_whisper_model: str = "small"
    faster_whisper_device: str = "cpu"
    faster_whisper_compute_type: str = "int8"
    asr_language: str = "en"
    wake_phrase_enabled: bool = False
    wake_phrase: str = "hola jarvis vamos a trabajar"
    wake_aliases: str = "jarvis,yarvis"
    wake_max_listen_seconds: float = 3.5
    vad_enabled: bool = True
    vad_speech_threshold: float = 0.015
    silence_timeout_seconds: float = 2.5
    max_listen_seconds: float = 10.0
    stdin_fallback: bool = True
    demo_command: str = "what can you do"


@dataclass()
class UIConfig:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 5050


@dataclass()
class TTSConfig:
    enabled: bool = True
    backend: str = "pyttsx3"
    rate: int = 180
    volume: float = 0.9
    stream_sentences: bool = True
    kokoro_voice: str = "af_heart"
    kokoro_lang_code: str = "a"
    piper_model_path: str = ""
    piper_binary: str = "piper"


@dataclass()
class SystemConfig:
    log_level: str = "INFO"
    safe_mode: bool = True
    allow_shutdown: bool = False


@dataclass()
class OllamaConfig:
    enabled: bool = True
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.1:8b"
    timeout_seconds: int = 120
    temperature: float = 0.2


@dataclass()
class GoogleConfig:
    enabled: bool = False
    credentials_path: str = ""
    token_path: str = ""


@dataclass()
class FilesystemConfig:
    allowed_roots: list[Path] = field(default_factory=lambda: [Path.cwd(), Path.home()])


@dataclass()
class MemoryConfig:
    database_path: Path = field(default_factory=lambda: Path("jarvis_data/agent_memory.sqlite3"))


@dataclass()
class AgentConfig:
    max_planning_steps: int = 4


@dataclass()
class SchedulerConfig:
    enable_calendar_watch: bool = True
    calendar_poll_seconds: int = 120
    reminder_window_minutes: int = 15


@dataclass()
class TaskConfig:
    max_attempts: int = 3
    retry_delay_seconds: int = 5


@dataclass()
class AppConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    system: SystemConfig = field(default_factory=SystemConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    filesystem: FilesystemConfig = field(default_factory=FilesystemConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    tasks: TaskConfig = field(default_factory=TaskConfig)
    music_dir: Path = field(default_factory=lambda: Path("jarvis/audio_assets/music"))

    @classmethod
    def from_env(cls) -> AppConfig:
        cfg = cls()
        cfg.audio.simulated_audio = _env_bool("JARVIS_SIMULATED_AUDIO", cfg.audio.simulated_audio)
        cfg.audio.clap_threshold = float(
            os.getenv("JARVIS_CLAP_THRESHOLD", cfg.audio.clap_threshold)
        )
        cfg.audio.clap_window_seconds = float(
            os.getenv("JARVIS_CLAP_WINDOW_SECONDS", cfg.audio.clap_window_seconds)
        )

        cfg.voice.vosk_model_path = os.getenv("JARVIS_VOSK_MODEL_PATH", cfg.voice.vosk_model_path)
        cfg.voice.backend = os.getenv("JARVIS_VOICE_BACKEND", cfg.voice.backend)
        cfg.voice.faster_whisper_model = os.getenv(
            "JARVIS_FASTER_WHISPER_MODEL",
            cfg.voice.faster_whisper_model,
        )
        cfg.voice.faster_whisper_device = os.getenv(
            "JARVIS_FASTER_WHISPER_DEVICE",
            cfg.voice.faster_whisper_device,
        )
        cfg.voice.faster_whisper_compute_type = os.getenv(
            "JARVIS_FASTER_WHISPER_COMPUTE_TYPE",
            cfg.voice.faster_whisper_compute_type,
        )
        cfg.voice.asr_language = os.getenv("JARVIS_ASR_LANGUAGE", cfg.voice.asr_language)
        cfg.voice.wake_phrase_enabled = _env_bool(
            "JARVIS_WAKE_PHRASE_ENABLED",
            cfg.voice.wake_phrase_enabled,
        )
        cfg.voice.wake_phrase = os.getenv("JARVIS_WAKE_PHRASE", cfg.voice.wake_phrase)
        cfg.voice.wake_aliases = os.getenv("JARVIS_WAKE_ALIASES", cfg.voice.wake_aliases)
        cfg.voice.wake_max_listen_seconds = float(
            os.getenv("JARVIS_WAKE_MAX_LISTEN_SECONDS", cfg.voice.wake_max_listen_seconds)
        )
        cfg.voice.vad_enabled = _env_bool("JARVIS_VAD_ENABLED", cfg.voice.vad_enabled)
        cfg.voice.vad_speech_threshold = float(
            os.getenv("JARVIS_VAD_SPEECH_THRESHOLD", cfg.voice.vad_speech_threshold)
        )
        cfg.voice.stdin_fallback = _env_bool("JARVIS_STDIN_FALLBACK", cfg.voice.stdin_fallback)
        cfg.voice.demo_command = os.getenv("JARVIS_DEMO_COMMAND", cfg.voice.demo_command)
        cfg.voice.silence_timeout_seconds = float(
            os.getenv("JARVIS_SILENCE_TIMEOUT_SECONDS", cfg.voice.silence_timeout_seconds)
        )
        cfg.voice.max_listen_seconds = float(
            os.getenv("JARVIS_MAX_LISTEN_SECONDS", cfg.voice.max_listen_seconds)
        )

        cfg.ui.enabled = _env_bool("JARVIS_ENABLE_UI", cfg.ui.enabled)
        cfg.ui.host = os.getenv("JARVIS_UI_HOST", cfg.ui.host)
        cfg.ui.port = int(os.getenv("JARVIS_UI_PORT", cfg.ui.port))

        cfg.tts.enabled = _env_bool("JARVIS_ENABLE_TTS", cfg.tts.enabled)
        cfg.tts.backend = os.getenv("JARVIS_TTS_BACKEND", cfg.tts.backend)
        cfg.tts.rate = int(os.getenv("JARVIS_TTS_RATE", cfg.tts.rate))
        cfg.tts.volume = float(os.getenv("JARVIS_TTS_VOLUME", cfg.tts.volume))
        cfg.tts.stream_sentences = _env_bool(
            "JARVIS_TTS_STREAM_SENTENCES", cfg.tts.stream_sentences
        )
        cfg.tts.kokoro_voice = os.getenv("JARVIS_KOKORO_VOICE", cfg.tts.kokoro_voice)
        cfg.tts.kokoro_lang_code = os.getenv("JARVIS_KOKORO_LANG_CODE", cfg.tts.kokoro_lang_code)
        cfg.tts.piper_model_path = os.getenv("JARVIS_PIPER_MODEL_PATH", cfg.tts.piper_model_path)
        cfg.tts.piper_binary = os.getenv("JARVIS_PIPER_BINARY", cfg.tts.piper_binary)

        cfg.system.log_level = os.getenv("JARVIS_LOG_LEVEL", cfg.system.log_level)
        cfg.system.safe_mode = _env_bool("JARVIS_SAFE_MODE", cfg.system.safe_mode)
        cfg.system.allow_shutdown = _env_bool("JARVIS_ALLOW_SHUTDOWN", cfg.system.allow_shutdown)

        cfg.ollama.enabled = _env_bool("JARVIS_OLLAMA_ENABLED", cfg.ollama.enabled)
        cfg.ollama.base_url = os.getenv("JARVIS_OLLAMA_BASE_URL", cfg.ollama.base_url)
        cfg.ollama.model = os.getenv("JARVIS_OLLAMA_MODEL", cfg.ollama.model)
        cfg.ollama.timeout_seconds = int(
            os.getenv("JARVIS_OLLAMA_TIMEOUT_SECONDS", cfg.ollama.timeout_seconds)
        )
        cfg.ollama.temperature = float(
            os.getenv("JARVIS_OLLAMA_TEMPERATURE", cfg.ollama.temperature)
        )

        cfg.google.enabled = _env_bool("JARVIS_GOOGLE_ENABLED", cfg.google.enabled)
        cfg.google.credentials_path = os.getenv(
            "JARVIS_GOOGLE_CREDENTIALS_PATH", cfg.google.credentials_path
        )
        cfg.google.token_path = os.getenv("JARVIS_GOOGLE_TOKEN_PATH", cfg.google.token_path)

        roots = os.getenv("JARVIS_ALLOWED_FILE_ROOTS")
        if roots:
            cfg.filesystem.allowed_roots = [
                Path(item).expanduser() for item in roots.split(":") if item.strip()
            ]

        memory_path = os.getenv("JARVIS_MEMORY_DB_PATH")
        if memory_path:
            cfg.memory.database_path = Path(memory_path).expanduser()

        cfg.agent.max_planning_steps = int(
            os.getenv("JARVIS_AGENT_MAX_PLANNING_STEPS", cfg.agent.max_planning_steps)
        )

        cfg.scheduler.enable_calendar_watch = _env_bool(
            "JARVIS_ENABLE_CALENDAR_WATCH",
            cfg.scheduler.enable_calendar_watch,
        )
        cfg.scheduler.calendar_poll_seconds = int(
            os.getenv("JARVIS_CALENDAR_POLL_SECONDS", cfg.scheduler.calendar_poll_seconds)
        )
        cfg.scheduler.reminder_window_minutes = int(
            os.getenv("JARVIS_REMINDER_WINDOW_MINUTES", cfg.scheduler.reminder_window_minutes)
        )

        cfg.tasks.max_attempts = int(os.getenv("JARVIS_TASK_MAX_ATTEMPTS", cfg.tasks.max_attempts))
        cfg.tasks.retry_delay_seconds = int(
            os.getenv("JARVIS_TASK_RETRY_DELAY_SECONDS", cfg.tasks.retry_delay_seconds)
        )

        music_dir = os.getenv("JARVIS_MUSIC_DIR")
        if music_dir:
            cfg.music_dir = Path(music_dir)

        return cfg


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
