"""Tests del almacén de memoria del agente (SQLite: interacciones y tareas)."""

from jarvis.agent.memory_store import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_PENDING,
    TASK_STATUS_RUNNING,
    AgentMemoryStore,
)


def make_store(tmp_path) -> AgentMemoryStore:
    return AgentMemoryStore(tmp_path / "memory" / "agent.sqlite3")


class TestInteractions:
    def test_record_and_read_back(self, tmp_path):
        store = make_store(tmp_path)
        store.record_interaction(
            "abre firefox", "abierto", "OPEN_APP", "app_launcher", "deterministic"
        )
        recent = store.recent_interactions()
        assert len(recent) == 1
        assert recent[0]["user_text"] == "abre firefox"
        assert recent[0]["intent_name"] == "OPEN_APP"

    def test_recent_interactions_respects_limit(self, tmp_path):
        store = make_store(tmp_path)
        for i in range(5):
            store.record_interaction(f"msg-{i}", "ok", "X", "", "deterministic")
        assert len(store.recent_interactions(limit=3)) == 3

    def test_recent_interactions_on_empty_db(self, tmp_path):
        assert make_store(tmp_path).recent_interactions() == []


class TestTasks:
    def test_create_task_is_pending_and_unique(self, tmp_path):
        store = make_store(tmp_path)
        task_id = store.create_task("resumir notas", "voice")
        task = store.get_task(task_id)
        assert task is not None
        assert task["status"] == TASK_STATUS_PENDING
        assert task_id != store.create_task("otra tarea", "chat")

    def test_update_task_lifecycle(self, tmp_path):
        store = make_store(tmp_path)
        task_id = store.create_task("goal", "chat")
        store.update_task(task_id, status=TASK_STATUS_RUNNING, attempts=1)
        assert store.get_task(task_id)["status"] == TASK_STATUS_RUNNING
        store.update_task(task_id, status=TASK_STATUS_COMPLETED, attempts=1, result_text="ok")
        task = store.get_task(task_id)
        assert task["status"] == TASK_STATUS_COMPLETED
        assert task["result_text"] == "ok"
        assert task["attempts"] == "1"

    def test_get_unknown_task_is_none(self, tmp_path):
        assert make_store(tmp_path).get_task("nope") is None

    def test_recent_tasks_lists_newest_first(self, tmp_path):
        store = make_store(tmp_path)
        first = store.create_task("a", "chat")
        second = store.create_task("b", "chat")
        tasks = store.recent_tasks()
        assert [t["task_id"] for t in tasks][:2] == [second, first]
