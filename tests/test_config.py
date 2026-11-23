"""Tests de la configuración (carga desde variables de entorno, bools, rutas)."""

from pathlib import Path

import pytest

from jarvis.core.config import AppConfig, _env_bool


@pytest.fixture()
def clean_env(monkeypatch):
    import os

    for key in list(os.environ):
        if key.startswith("JARVIS_"):
            monkeypatch.delenv(key, raising=False)


class TestEnvBool:
    @pytest.mark.parametrize("raw", ["1", "true", "TRUE", "Yes", "on", " ON "])
    def test_truthy_values(self, monkeypatch, raw):
        monkeypatch.setenv("JARVIS_TEST_FLAG", raw)
        assert _env_bool("JARVIS_TEST_FLAG", False) is True

    @pytest.mark.parametrize("raw", ["0", "false", "no", "off", "", "maybe"])
    def test_falsey_values(self, monkeypatch, raw):
        monkeypatch.setenv("JARVIS_TEST_FLAG", raw)
        assert _env_bool("JARVIS_TEST_FLAG", True) is False

    def test_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("JARVIS_TEST_FLAG", raising=False)
        assert _env_bool("JARVIS_TEST_FLAG", True) is True
        assert _env_bool("JARVIS_TEST_FLAG", False) is False


class TestFromEnv:
    def test_defaults_load_without_env(self, clean_env):
        cfg = AppConfig.from_env()
        assert cfg.system.log_level
        assert cfg.ollama.timeout_seconds > 0
        assert cfg.agent.max_planning_steps >= 1

    def test_env_overrides_ollama_settings(self, clean_env, monkeypatch):
        monkeypatch.setenv("JARVIS_OLLAMA_ENABLED", "false")
        monkeypatch.setenv("JARVIS_OLLAMA_MODEL", "test-model")
        monkeypatch.setenv("JARVIS_OLLAMA_TEMPERATURE", "0.5")
        cfg = AppConfig.from_env()
        assert cfg.ollama.enabled is False
        assert cfg.ollama.model == "test-model"
        assert cfg.ollama.temperature == 0.5

    def test_allowed_roots_parsed_as_path_list(self, clean_env, monkeypatch):
        monkeypatch.setenv("JARVIS_ALLOWED_FILE_ROOTS", "/tmp:/home/user/docs")
        cfg = AppConfig.from_env()
        assert cfg.filesystem.allowed_roots == [Path("/tmp"), Path("/home/user/docs")]

    def test_agent_steps_override(self, clean_env, monkeypatch):
        monkeypatch.setenv("JARVIS_AGENT_MAX_PLANNING_STEPS", "7")
        cfg = AppConfig.from_env()
        assert cfg.agent.max_planning_steps == 7

    def test_memory_db_path_override(self, clean_env, monkeypatch):
        monkeypatch.setenv("JARVIS_MEMORY_DB_PATH", "/tmp/jarvis-test.sqlite3")
        cfg = AppConfig.from_env()
        assert cfg.memory.database_path == Path("/tmp/jarvis-test.sqlite3")
