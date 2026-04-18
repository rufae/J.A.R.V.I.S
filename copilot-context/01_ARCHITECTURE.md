Design a clean layered architecture:

LAYERS:

1. INPUT LAYER
- Microphone stream
- Audio preprocessing
- Clap detection

2. INTELLIGENCE LAYER
- Speech-to-text engine
- Intent parser
- State machine controller

3. EXECUTION LAYER
- System actions
- Media control
- App launcher

4. OUTPUT LAYER
- Text-to-speech engine
- UI dashboard updates

5. CONTROL LAYER
- State manager (IDLE, LISTENING, PROCESSING, EXECUTING, SPEAKING)

RULES:
- No direct coupling between input and execution
- All communication must pass through state manager or event bus
- Every module must be independently testable