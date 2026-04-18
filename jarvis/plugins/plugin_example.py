from __future__ import annotations

from jarvis.core.command_registry import CommandResult
from jarvis.core.intent_parser import Intent
from jarvis.core.plugin_manager import PluginContext


def register(context: PluginContext) -> None:
    context.parser.register_rule(r"^jarvis\s+status$", "SYSTEM_STATUS")
    context.parser.register_rule(r"^jarvis\s+ping$", "SYSTEM_PING")
    context.commands.register("SYSTEM_PING", _handle_ping)


def _handle_ping(_intent: Intent) -> CommandResult:
    return CommandResult(True, "Pong. All plugin channels are online.")
