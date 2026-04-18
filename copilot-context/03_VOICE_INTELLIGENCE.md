Voice intelligence system responsible for converting speech into structured commands.

COMPONENTS:
- Speech-to-text engine (Vosk or Whisper offline)
- Continuous listening mode after wake event
- Silence detection timeout
- Text normalization layer

OUTPUT:
- Clean text command string
- Sent to intent parser

REQUIREMENTS:
- Must support real-time transcription
- Must be optimized for low latency