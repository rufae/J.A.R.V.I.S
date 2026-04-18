Define full system lifecycle.

STARTUP FLOW:

1. Initialize config
2. Start state manager
3. Start audio system (clap detector)
4. Start UI (optional)
5. Enter IDLE state

RUNTIME FLOW:

IDLE
→ detect clap
→ WAKE_EVENT
→ LISTENING

LISTENING
→ speech capture
→ STT conversion
→ intent parsing
→ EXECUTING

EXECUTING
→ run system/media action
→ send response to TTS
→ SPEAKING

SPEAKING
→ finish output
→ return to IDLE

RULES:
- Only one active state at a time
- No parallel command execution conflicts