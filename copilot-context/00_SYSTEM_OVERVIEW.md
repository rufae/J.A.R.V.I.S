You are building a production-grade local AI assistant system called JARVIS.

This system is NOT a script. It is a modular, event-driven, multi-threaded assistant running on Ubuntu Linux.

GOAL:
Create a real-time voice-controlled assistant that can:
- Detect wake triggers (claps)
- Listen to voice commands
- Convert speech to intent
- Execute system actions
- Provide spoken responses
- Display a real-time UI dashboard

CORE PRINCIPLES:
- Fully modular architecture
- No monolithic scripts
- Event-driven communication between modules
- Async or multi-threaded execution
- Extensible plugin-based command system

SYSTEM DESIGN MUST SUPPORT:
- AI integration in future (LLM-ready)
- Smart automation
- Desktop control
- Voice interaction loop