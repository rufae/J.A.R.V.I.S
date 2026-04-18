from __future__ import annotations

import logging
import os
import shlex
import subprocess
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class AppLauncher:
    def __init__(self) -> None:
        self._app_map = {
            "vscode": "code",
            "code": "code",
            "firefox": "firefox",
            "terminal": "gnome-terminal",
        }
        self._desktop_index = self._build_desktop_index()

    def launch(self, app_name: str) -> tuple[bool, str]:
        normalized = app_name.strip().lower()
        command = self._app_map.get(normalized) or self._desktop_index.get(normalized) or normalized

        try:
            subprocess.Popen(shlex.split(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            LOGGER.info("Launched app command=%s", command)
            return True, f"Opening {normalized}."
        except FileNotFoundError:
            LOGGER.warning("Application command not found: %s", command)
            return False, f"I cannot find the app '{normalized}'."
        except Exception:
            LOGGER.exception("Failed to launch app %s", command)
            return False, f"I could not open {normalized}."

    def discover_apps(self, limit: int = 100) -> list[str]:
        app_names = set(self._app_map.keys())
        app_names.update(self._desktop_index.keys())
        return sorted(app_names)[:limit]

    def _build_desktop_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for directory in self._desktop_entry_dirs():
            if not directory.exists():
                continue
            for entry in directory.glob("*.desktop"):
                try:
                    content = entry.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                name = self._extract_field(content, "Name")
                command = self._extract_field(content, "Exec")
                if not name or not command:
                    continue
                cleaned = shlex.split(command.replace("%U", "").replace("%u", "").replace("%F", "").replace("%f", ""))
                if not cleaned:
                    continue
                index[name.strip().lower()] = cleaned[0]
        return index

    @staticmethod
    def _extract_field(content: str, field: str) -> str:
        prefix = f"{field}="
        for line in content.splitlines():
            if line.startswith(prefix):
                return line.split("=", 1)[1].strip()
        return ""

    @staticmethod
    def _desktop_entry_dirs() -> list[Path]:
        home = Path.home()
        xdg_data_home = Path(os.getenv("XDG_DATA_HOME", home / ".local/share"))
        return [
            xdg_data_home / "applications",
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
        ]
