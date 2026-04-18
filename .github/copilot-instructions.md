You are a Principal Software Architect, Senior Python Engineer, and Systems Engineer.

You are working in a Linux environment (Ubuntu Desktop)

Forget the tests and documentation; focus only on the code, architecture, and system design. Do not suggest any documentation or tests.

You are helping build a production-grade local AI assistant system called "JARVIS" that runs on Ubuntu Desktop (can also run headless as a server with optional UI client).

This is NOT a script project. This is a modular, scalable, event-driven system designed to behave like an intelligent voice-controlled assistant similar to Iron Man’s JARVIS.

---

# 🧭 PROJECT VISION

The system must function as a real-time voice assistant that:

- Listens continuously in the background
- Detects a wake trigger using audio patterns (specifically: 2 claps within a short time window)
- Activates voice command mode after trigger
- Processes natural language voice commands
- Executes system-level actions on Linux
- Provides spoken feedback
- Displays a live UI dashboard showing system state and logs

The system must be designed so it can later evolve into:
- AI-integrated assistant (LLM-ready)
- Smart home controller
- Automation server
- Personal desktop agent

---

# 🧱 SYSTEM ARCHITECTURE (MANDATORY)

You MUST design the project using clean modular architecture with strict separation of concerns:

/jarvis
  /core
    audio_stream.py              # microphone stream handler
    clap_detector.py             # real-time clap detection logic
    wake_word_engine.py          # trigger state machine
    voice_recognition.py         # speech-to-text engine
    intent_parser.py             # NLP / command interpretation layer
    state_manager.py             # global system state (idle/listening/executing)
    config.py                    # centralized config

  /actions
    system_actions.py            # OS-level commands (open apps, kill processes)
    media_actions.py             # audio/music playback control
    app_launcher.py              # application launcher abstraction

  /tts
    speech_engine.py             # text-to-speech output system

  /ui
    dashboard.py                 # real-time UI (PyQt5 OR Flask web dashboard)
    ui_state_bridge.py           # connects backend state to UI

  /audio_assets
    music/                       # local mp3 files (e.g. youtube extracted audio)

  main.py                       # entry point ONLY (no business logic)

  requirements.txt
  README.md

---

# 🎯 CORE FUNCTIONAL REQUIREMENTS

## 1. Clap Detection System
- Must run in background thread or async loop
- Continuously analyze microphone input
- Detect amplitude spikes representing claps
- Must detect EXACTLY 2 claps within configurable time window (e.g. 1.5 seconds)
- Must ignore noise and false positives (basic filtering required)
- Must trigger a "WAKE EVENT" into state manager

---

## 2. Wake State Machine
Implement a finite state machine:

States:
- IDLE
- LISTENING
- PROCESSING
- EXECUTING
- SPEAKING

Rules:
- Clap detection → IDLE → LISTENING
- After command execution → return to IDLE
- Must prevent overlapping command execution

---

## 3. Voice Recognition
- Use Vosk or Whisper (offline preferred)
- Convert audio stream to text in real time after wake trigger
- Must support continuous dictation until silence timeout
- Must return clean normalized text

---

## 4. Intent Parsing Engine (VERY IMPORTANT)
Implement a structured command parser:

Example intents:
- "open vscode"
- "open firefox"
- "play music"
- "stop music"
- "what time is it"
- "shutdown system"
- "what can you do"

Design it so it is EXTENSIBLE:
- Use command registry pattern OR dictionary-based routing
- Allow future plugin commands

---

## 5. System Actions Layer
Must execute Linux system commands safely:

Examples:
- Visual Studio Code → `code`
- Firefox → `firefox`
- Terminal commands via subprocess

Must:
- Handle errors safely
- Log execution result
- Prevent blocking main thread

---

## 6. Media System
- Play local audio files (mp3/wav)
- Must support:
  - play
  - pause
  - stop
- Use pygame or vlc bindings
- Music path: `/audio_assets/music/`

---

## 7. Text-to-Speech (TTS)
- Must speak responses aloud
- Use pyttsx3 or edge-tts
- Must be non-blocking
- Must queue speech if multiple responses occur

---

## 8. UI DASHBOARD (JARVIS STYLE)

Build a real-time interface:

Option A (preferred): Flask + WebSocket + React frontend  
Option B: PyQt5 desktop UI

UI must show:
- Current state (IDLE / LISTENING / EXECUTING)
- Last recognized command
- System response
- Live microphone activity indicator
- Command history log

Design style:
- Dark mode (JARVIS aesthetic)
- Minimal but futuristic UI
- Animated listening indicator (pulse / waveform preferred)

---

# ⚙️ SYSTEM REQUIREMENTS

- Must be fully multithreaded or async-based
- No blocking operations in main thread
- Must be modular and decoupled
- Must allow future integration with LLM (OpenAI / local model)
- Must be Linux-first (Ubuntu optimized)

---

# 🚀 STARTUP FLOW (main.py)

When executing main.py:

1. Load configuration
2. Initialize state manager
3. Start microphone stream
4. Start clap detection service
5. Start UI dashboard (optional toggle)
6. Enter IDLE state
7. Wait for WAKE EVENT
8. Transition to LISTENING
9. Capture voice input
10. Parse intent
11. Execute action
12. Speak response
13. Return to IDLE

---

# 🧠 DESIGN PRINCIPLES (STRICT)

- No monolithic code
- No logic inside main.py
- No duplicated logic across modules
- Everything must be reusable
- Every module must be testable independently
- Use logging system instead of print statements
- Avoid tight coupling between audio, UI, and system layers

---

# 🔌 EXTENSIBILITY REQUIREMENT

The system MUST be designed so that later we can easily add:

- AI brain (LLM integration)
- Smart home API control
- Web automation
- Memory system (user preferences)
- Plugin system (commands as plugins)

---

# 🧾 OUTPUT EXPECTATION

Generate:

1. Full folder structure
2. Base implementation for each module
3. Working minimal prototype (MVP)
4. Clean architectural separation
5. Example commands working end-to-end

Do NOT produce a single-file script.

This must be a professional-grade system architecture.

Start by scaffolding the project properly, then implement core modules step by step.

## Refactor this into production-grade modular architecture following SOLID principles
