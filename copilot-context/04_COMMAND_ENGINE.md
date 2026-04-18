Design an intent-based command engine.

GOAL:
Convert natural language into structured actions.

EXAMPLES:
- "open vscode" → OPEN_APP:vscode
- "open firefox" → OPEN_APP:firefox
- "play music" → MEDIA_PLAY
- "stop music" → MEDIA_STOP
- "what time is it" → SYSTEM_TIME

ARCHITECTURE:
- Use registry-based command system
- Each command must be a handler function
- Must support dynamic command registration

RULES:
- No hardcoded if-else chains
- Must be extensible via plugins