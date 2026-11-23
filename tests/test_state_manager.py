"""Tests del gestor de estado (transiciones, listeners, snapshots)."""

import threading

import pytest

from jarvis.core.state_manager import AssistantState, StateManager


class TestTransitions:
    def test_initial_state_is_idle(self):
        assert StateManager().state is AssistantState.IDLE

    def test_transition_to_updates_state(self):
        manager = StateManager()
        manager.transition_to(AssistantState.LISTENING)
        assert manager.state is AssistantState.LISTENING
        manager.transition_to(AssistantState.SPEAKING)
        assert manager.state is AssistantState.SPEAKING

    def test_setters_are_reflected_in_snapshot(self):
        manager = StateManager()
        manager.set_last_command("open firefox")
        manager.set_last_response("done")
        manager.set_last_intent("OPEN_APP")
        manager.set_last_tool("app_launcher")
        manager.set_agent_mode("agent")
        manager.set_mic_level(0.42)
        manager.set_active_task("t-1", "RUNNING")
        snap = manager.snapshot()
        assert snap.last_command == "open firefox"
        assert snap.last_response == "done"
        assert snap.last_intent == "OPEN_APP"
        assert snap.last_tool == "app_launcher"
        assert snap.agent_mode == "agent"
        assert snap.mic_level == 0.42
        assert snap.active_task_id == "t-1"
        assert snap.active_task_status == "RUNNING"

    def test_history_keeps_last_50_in_order(self):
        manager = StateManager()
        manager.add_history_entry("first")
        manager.add_history_entry("second")
        assert manager.history() == ["first", "second"]
        for i in range(60):
            manager.add_history_entry(f"e{i}")
        assert len(manager.history()) == 50
        assert manager.history()[-1] == "e59"


class TestListeners:
    def test_subscribed_listener_receives_snapshots(self):
        manager = StateManager()
        seen = []
        manager.subscribe(lambda snap: seen.append(snap.state))
        manager.transition_to(AssistantState.PROCESSING)
        assert AssistantState.PROCESSING in seen

    def test_listener_error_propagates_but_state_is_updated(self):
        # El snapshot se notifica fuera del lock: el cambio ya está aplicado
        # aunque un listener reviente (responsabilidad del listener).
        manager = StateManager()

        def broken(_snap):
            raise RuntimeError("listener exploded")

        manager.subscribe(broken)
        with pytest.raises(RuntimeError):
            manager.transition_to(AssistantState.EXECUTING)
        assert manager.state is AssistantState.EXECUTING


class TestConcurrency:
    def test_concurrent_writes_are_safe(self):
        manager = StateManager()
        errors = []

        def work():
            try:
                for i in range(100):
                    manager.set_last_command(f"cmd-{i}")
                    _ = manager.snapshot()
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=work) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
