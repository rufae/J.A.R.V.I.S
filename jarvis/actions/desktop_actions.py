from __future__ import annotations

import logging
import os
import shlex
import subprocess
from typing import Iterable


LOGGER = logging.getLogger(__name__)


class DesktopActions:
    def __init__(self) -> None:
        self._pyautogui = self._load_pyautogui()

    def type_text(self, text: str, interval: float = 0.02) -> tuple[bool, str]:
        if not text:
            return False, "No text provided."
        if self._pyautogui is not None:
            try:
                self._pyautogui.write(text, interval=interval)
                return True, "Typed text into the active window."
            except Exception:
                LOGGER.exception("pyautogui typing failed")
        return self._run_xdotool(["type", "--delay", str(max(1, int(interval * 1000))), text])

    def press_keys(self, keys: Iterable[str]) -> tuple[bool, str]:
        normalized = [key.strip().lower() for key in keys if key.strip()]
        if not normalized:
            return False, "No keys provided."
        if self._pyautogui is not None:
            try:
                self._pyautogui.hotkey(*normalized)
                return True, f"Pressed hotkey {' + '.join(normalized)}."
            except Exception:
                LOGGER.exception("pyautogui hotkey failed")
        return self._run_xdotool(["key", "+".join(normalized)])

    def focus_window(self, window_name: str) -> tuple[bool, str]:
        if not window_name.strip():
            return False, "Window name is required."
        return self._run_xdotool(["search", "--name", window_name, "windowactivate"])

    def _run_xdotool(self, args: list[str]) -> tuple[bool, str]:
        if not os.getenv("DISPLAY") and not os.getenv("WAYLAND_DISPLAY"):
            return False, "Desktop automation requires an active graphical session."

        try:
            process = subprocess.run(
                ["xdotool", *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except FileNotFoundError:
            return False, "xdotool is not installed and pyautogui is unavailable."
        except Exception:
            LOGGER.exception("Desktop automation command failed")
            return False, "Desktop automation failed."

        output = (process.stdout or process.stderr).strip()
        if process.returncode != 0:
            return False, output or "Desktop automation command failed."
        return True, output or "Desktop automation command executed."

    @staticmethod
    def _load_pyautogui():
        try:
            import pyautogui

            pyautogui.FAILSAFE = True
            return pyautogui
        except Exception:
            return None
