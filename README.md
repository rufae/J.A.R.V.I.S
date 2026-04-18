# JARVIS

Production-grade local AI assistant for Ubuntu Linux with offline-first voice control, Ollama-based agent orchestration, desktop automation, filesystem tooling, Google Workspace integration, persistent memory, background task execution, and a pluggable real-time speech stack.

## Architecture

JARVIS is structured as a layered, event-driven assistant instead of a monolithic script.

```text
jarvis/
  actions/
    app_launcher.py
    desktop_actions.py
    file_actions.py
    media_actions.py
    system_actions.py
  agent/
    brain.py
    memory_store.py
    models.py
    orchestrator.py
    planner.py
    task_engine.py
  core/
    audio_stream.py
    clap_detector.py
    command_registry.py
    config.py
    intent_parser.py
    plugin_manager.py
    state_manager.py
    voice_recognition.py
    wake_word_engine.py
  integrations/
    google_workspace.py
  services/
    calendar_watch_service.py
  tts/
    speech_engine.py
  ui/
    dashboard.py
    ui_state_bridge.py
  plugins/
    plugin_example.py
  audio_assets/
    music/
credentials/
jarvis_data/
main.py
.env
requirements.txt
```

## Current Capabilities

- Continuous audio pipeline with double-clap wake detection
- State machine lifecycle: `IDLE`, `LISTENING`, `PROCESSING`, `EXECUTING`, `SPEAKING`
- Offline speech path with configurable `faster-whisper` or `Vosk` backends
- Configurable local TTS with `Kokoro`, `Piper`, or `pyttsx3` fallback
- Hybrid command routing: deterministic intents plus Ollama agent mode
- Multi-step tool planning through the local model
- Persistent SQLite memory for interactions and queued tasks
- Background task queue with retries and spoken completion/failure updates
- Linux app launching, shell command execution, file inspection and file writing inside allowed roots
- Desktop automation with window focus, typing and hotkeys
- Google Calendar and Contacts integration through OAuth
- Background calendar watch service with reminders
- Real-time Flask + Socket.IO dashboard showing state, agent mode, tool usage and task activity

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Setup

The project loads configuration automatically from `.env` on startup.

Prepared paths:

- `./credentials/google-client-secret.json`
- `./credentials/google-token.json`
- `./jarvis_data/agent_memory.sqlite3`

## Required External Services

### Ollama

You need a local Ollama daemon running and a local model installed.

```bash
ollama serve
ollama pull llama3.1:8b
```

Relevant `.env` keys:

```env
JARVIS_OLLAMA_ENABLED=1
JARVIS_OLLAMA_BASE_URL=http://127.0.0.1:11434
JARVIS_OLLAMA_MODEL=llama3.1:8b
```

### Google Calendar and Contacts

To enable Google integrations:

1. Create OAuth desktop credentials in Google Cloud.
2. Place the client secret JSON at `./credentials/google-client-secret.json`.
3. Set `JARVIS_GOOGLE_ENABLED=1` in `.env`.
4. On first use, JARVIS will run the local OAuth flow and create `./credentials/google-token.json`.

Relevant `.env` keys:

```env
JARVIS_GOOGLE_ENABLED=1
JARVIS_GOOGLE_CREDENTIALS_PATH=./credentials/google-client-secret.json
JARVIS_GOOGLE_TOKEN_PATH=./credentials/google-token.json
```

## Real-Time Voice Stack

For fluid conversation, real-time response, and zero vendor cost, the strongest current local path is:

- STT: `faster-whisper`
- speech turn detection: silence/VAD capture, optionally complemented by `silero-vad`
- TTS: `Kokoro` for the most natural local voice quality
- Alternative TTS: `Piper` when you want a lighter and very fast local runtime

Open-source references considered for this direction:

- `SYSTRAN/faster-whisper`: fast Whisper inference with strong community real-time integrations
- `snakers4/silero-vad`: lightweight VAD with very low CPU latency
- `hexgrad/kokoro`: open-weight local TTS with much more natural output than classic offline engines
- `OHF-Voice/piper1-gpl`: fast local neural TTS used by Home Assistant and other local voice ecosystems

Recommended CPU profile:

```env
JARVIS_VOICE_BACKEND=faster-whisper
JARVIS_FASTER_WHISPER_MODEL=small
JARVIS_FASTER_WHISPER_DEVICE=cpu
JARVIS_FASTER_WHISPER_COMPUTE_TYPE=int8
JARVIS_TTS_BACKEND=kokoro
JARVIS_KOKORO_VOICE=af_heart
```

Lighter TTS profile:

```env
JARVIS_TTS_BACKEND=piper
JARVIS_PIPER_MODEL_PATH=/absolute/path/to/voice.onnx
```

## Run

```bash
python3 main.py
```

## Core Configuration

Main variables already included in `.env`:

```env
JARVIS_SAFE_MODE=1
JARVIS_ALLOW_SHUTDOWN=0
JARVIS_SIMULATED_AUDIO=0
JARVIS_VOICE_BACKEND=faster-whisper
JARVIS_VOSK_MODEL_PATH=
JARVIS_FASTER_WHISPER_MODEL=small
JARVIS_VAD_ENABLED=1
JARVIS_ENABLE_UI=1
JARVIS_ENABLE_TTS=1
JARVIS_TTS_BACKEND=kokoro
JARVIS_ALLOWED_FILE_ROOTS=.:/home/rafael
JARVIS_AGENT_MAX_PLANNING_STEPS=4
JARVIS_ENABLE_CALENDAR_WATCH=1
JARVIS_CALENDAR_POLL_SECONDS=120
JARVIS_REMINDER_WINDOW_MINUTES=15
JARVIS_TASK_MAX_ATTEMPTS=3
JARVIS_TASK_RETRY_DELAY_SECONDS=5
```

## Example Commands

Deterministic commands:

- `open vscode`
- `show apps`
- `read file ./README.md`
- `list files in ./jarvis`
- `find files *.py in ./jarvis`
- `what's on my calendar`
- `search contact rafael`
- `do task summarize the python files in ./jarvis and write the result to ./jarvis_data/report.txt`
- `show tasks`

Agent mode prompts:

- `jarvis open firefox and then type github copilot`
- `assistant check my upcoming meetings and tell me what matters first`
- `jarvis search my contacts for ana and prepare a note file in jarvis_data`

## Security Notes

- `.env` is ignored through `.gitignore`.
- Google OAuth credentials and token files are ignored through `.gitignore`.
- Filesystem actions are restricted by `JARVIS_ALLOWED_FILE_ROOTS`.
- Shell command execution is only exposed to the agent when `JARVIS_SAFE_MODE=0`.

## Operational Notes

- If you want the most fluid local STT, prefer `faster-whisper` over `Vosk`.
- If you want the most natural free local voice, prefer `Kokoro`; if you want a lighter and very fast TTS runtime, use `Piper`.
- If no STT backend is available, the system can still work with fallback command input.
- Desktop automation requires an active graphical session and preferably `xdotool` installed.
- Calendar reminders run in background only when Google integration is enabled and `JARVIS_ENABLE_CALENDAR_WATCH=1`.
