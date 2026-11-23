from __future__ import annotations

import datetime as dt
import logging
import shlex
import subprocess
from concurrent.futures import Future, ThreadPoolExecutor

from jarvis.actions.app_launcher import AppLauncher

LOGGER = logging.getLogger(__name__)


class SystemActions:
    def __init__(self, allow_shutdown: bool = False) -> None:
        self._allow_shutdown = allow_shutdown
        self._launcher = AppLauncher()
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="system-actions")

    def open_app(self, app_name: str) -> Future[tuple[bool, str]]:
        return self._executor.submit(self._launcher.launch, app_name)

    def get_time(self) -> Future[tuple[bool, str]]:
        return self._executor.submit(self._get_time_sync)

    def close_app(self, app_name: str) -> Future[tuple[bool, str]]:
        return self._executor.submit(self._close_app_sync, app_name)

    def shutdown_system(self) -> Future[tuple[bool, str]]:
        return self._executor.submit(self._shutdown_sync)

    def capabilities(self) -> Future[tuple[bool, str]]:
        return self._executor.submit(
            lambda: (
                True,
                "I can open and close apps, inspect or modify files, search directories, "
                "query calendar and contacts, play or stop music, tell the time, "
                "and coordinate local AI actions.",
            )
        )

    def status(self) -> Future[tuple[bool, str]]:
        return self._executor.submit(lambda: (True, "Core systems are online."))

    def list_available_apps(self) -> Future[tuple[bool, str, list[str]]]:
        return self._executor.submit(self._list_apps_sync)

    def execute_shell_command(self, command: str) -> Future[tuple[bool, str]]:
        return self._executor.submit(self._execute_shell_command_sync, command)

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _get_time_sync() -> tuple[bool, str]:
        now = dt.datetime.now().strftime("%H:%M")
        return True, f"It is {now}."

    def _shutdown_sync(self) -> tuple[bool, str]:
        if not self._allow_shutdown:
            return False, "Shutdown is disabled in safe mode."

        try:
            subprocess.Popen(
                ["shutdown", "-h", "now"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, "Shutting down the system now."
        except Exception:
            LOGGER.exception("Shutdown command failed")
            return False, "I could not execute shutdown."

    def _close_app_sync(self, app_name: str) -> tuple[bool, str]:
        normalized = app_name.strip().lower()
        if not normalized:
            return False, "Missing app name."

        # Try command and canonical app name to maximize hit rate.
        command = self._launcher.resolve_command(normalized)
        candidates = [normalized]
        if command and command not in candidates:
            candidates.append(command)

        for candidate in candidates:
            try:
                process = subprocess.run(
                    ["pkill", "-f", candidate],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except Exception:
                LOGGER.exception("Close app command failed for candidate=%s", candidate)
                continue

            if process.returncode == 0:
                return True, f"Closed {normalized}."

        return False, f"I could not find a running process for {normalized}."

    def _list_apps_sync(self) -> tuple[bool, str, list[str]]:
        apps = self._launcher.discover_apps()
        preview = ", ".join(apps[:10]) if apps else "no indexed applications"
        return True, f"Available applications: {preview}", apps

    @staticmethod
    def _execute_shell_command_sync(command: str) -> tuple[bool, str]:
        try:
            process = subprocess.run(
                shlex.split(command),
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception:
            LOGGER.exception("Shell command execution failed")
            return False, "Shell command execution failed."

        output = (process.stdout or process.stderr).strip()
        message = output[:4000] if output else f"Command exited with code {process.returncode}."
        return process.returncode == 0, message
