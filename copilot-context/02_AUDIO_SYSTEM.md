Implement real-time audio processing system.

FEATURES:
- Continuous microphone stream capture
- Low latency audio buffering
- Clap detection algorithm (amplitude spike detection)
- Detection rule: 2 claps within configurable time window (default 1.5s)

REQUIREMENTS:
- Must run in background thread
- Must not block main system
- Must filter noise and false positives
- Must emit "WAKE_EVENT" when claps detected

OUTPUT:
- Event-based signal to state manager