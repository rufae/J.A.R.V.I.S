Design a plugin system for future expansion.

GOAL:
Allow new commands without modifying core system.

PLUGIN STRUCTURE:
- Each plugin registers commands
- Each plugin defines handlers

EXAMPLE:
plugin_weather.py
plugin_smart_home.py
plugin_ai_brain.py

RULES:
- Dynamic loading of plugins
- Register commands at runtime
- No core modifications required for new features

FUTURE EXTENSIONS:
- LLM integration (OpenAI / local model)
- Home automation APIs
- Personal memory system