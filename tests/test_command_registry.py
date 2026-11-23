"""Tests del registro de comandos (registro, despacho, errores de handlers)."""

from jarvis.core.command_registry import CommandRegistry, CommandResult
from jarvis.core.intent_parser import Intent


def intent(name: str) -> Intent:
    return Intent(name=name, entities={}, text="")


def test_dispatch_registered_handler():
    registry = CommandRegistry()
    registry.register("open_app", lambda i: CommandResult(True, f"opened {i.entities.get('app')}"))
    result = registry.dispatch(Intent(name="OPEN_APP", entities={"app": "firefox"}))
    assert result.success is True
    assert result.message == "opened firefox"


def test_registry_is_case_insensitive():
    registry = CommandRegistry()
    registry.register("Open_App", lambda i: CommandResult(True, "ok"))
    assert registry.dispatch(intent("open_app")).success is True
    assert registry.dispatch(intent("OPEN_APP")).success is True


def test_unknown_command_is_a_graceful_failure():
    result = CommandRegistry().dispatch(intent("NOT_A_REAL_INTENT"))
    assert result.success is False
    assert "do not recognize" in result.message.lower()


def test_handler_exception_becomes_error_result():
    def boom(i):
        raise RuntimeError("handler exploded")

    registry = CommandRegistry()
    registry.register("boom", boom)
    result = registry.dispatch(intent("BOOM"))
    assert result.success is False
    assert result.message == "Internal command execution error."


def test_re_register_overwrites_handler():
    registry = CommandRegistry()
    registry.register("x", lambda i: CommandResult(True, "first"))
    registry.register("x", lambda i: CommandResult(True, "second"))
    assert registry.dispatch(intent("x")).message == "second"
