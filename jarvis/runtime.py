from __future__ import annotations

import concurrent.futures
import logging
import threading
import time

from jarvis.actions.desktop_actions import DesktopActions
from jarvis.actions.file_actions import FileActions
from jarvis.actions.media_actions import MediaActions
from jarvis.actions.system_actions import SystemActions
from jarvis.agent.brain import OllamaBrain
from jarvis.agent.memory_store import AgentMemoryStore
from jarvis.agent.models import AgentExecutionResult
from jarvis.agent.models import ToolDefinition
from jarvis.agent.orchestrator import AgentOrchestrator
from jarvis.agent.planner import AgentPlanner
from jarvis.agent.task_engine import TaskExecutionEngine
from jarvis.core.audio_stream import AudioStreamService
from jarvis.core.clap_detector import ClapDetectorService
from jarvis.core.command_registry import CommandRegistry
from jarvis.core.command_registry import CommandResult
from jarvis.core.config import AppConfig
from jarvis.core.intent_parser import Intent
from jarvis.core.intent_parser import IntentParser
from jarvis.core.plugin_manager import PluginManager
from jarvis.core.state_manager import AssistantState
from jarvis.core.state_manager import StateManager
from jarvis.core.voice_recognition import VoiceRecognitionEngine
from jarvis.core.wake_word_engine import WakeWordEngine
from jarvis.integrations.google_workspace import GoogleWorkspaceGateway
from jarvis.services.calendar_watch_service import CalendarWatchService
from jarvis.tts.speech_engine import SpeechEngine
from jarvis.ui.dashboard import DashboardServer
from jarvis.ui.ui_state_bridge import UIStateBridge


LOGGER = logging.getLogger(__name__)


class JarvisApplication:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._shutdown = threading.Event()
        self._command_lock = threading.Lock()

        self.state_manager = StateManager()
        self.audio_stream = AudioStreamService(config.audio, self.state_manager)
        self.wake_engine = WakeWordEngine(self.state_manager)
        self.clap_detector = ClapDetectorService(
            audio_stream=self.audio_stream,
            config=config.audio,
            on_wake_event=self.wake_engine.emit_wake_event,
        )
        self.voice = VoiceRecognitionEngine(config.voice)
        self.intent_parser = IntentParser()
        self.command_registry = CommandRegistry()
        self.plugin_manager = PluginManager()

        self.system_actions = SystemActions(allow_shutdown=config.system.allow_shutdown)
        self.desktop_actions = DesktopActions()
        self.file_actions = FileActions(config.filesystem.allowed_roots)
        self.media_actions = MediaActions(config.music_dir)
        self.google_workspace = GoogleWorkspaceGateway(config.google)
        self.speech_engine = SpeechEngine(config.tts)
        self.brain = OllamaBrain(config.ollama)
        self.agent_orchestrator = AgentOrchestrator(
            self.brain,
            planner=AgentPlanner(self.brain, max_steps=config.agent.max_planning_steps),
        )
        self.memory_store = AgentMemoryStore(config.memory.database_path)
        self.task_engine = TaskExecutionEngine(
            memory_store=self.memory_store,
            executor=self._execute_agent_goal,
            max_attempts=config.tasks.max_attempts,
            retry_delay_seconds=config.tasks.retry_delay_seconds,
            on_task_update=self._on_task_update,
        )
        self.calendar_watch = CalendarWatchService(
            gateway=self.google_workspace,
            poll_seconds=config.scheduler.calendar_poll_seconds,
            reminder_window_minutes=config.scheduler.reminder_window_minutes,
            on_reminder=self._handle_background_reminder,
        )

        self.ui_bridge = UIStateBridge(self.state_manager)
        self.dashboard = DashboardServer(config.ui.host, config.ui.port, self.ui_bridge)

    def bootstrap(self) -> None:
        self._register_builtin_commands()
        self._register_agent_tools()
        self.plugin_manager.load(self.intent_parser, self.command_registry)
        self.task_engine.start()
        self.audio_stream.start()
        self.clap_detector.start()
        self.speech_engine.start()
        if self._config.scheduler.enable_calendar_watch:
            self.calendar_watch.start()
        if self._config.ui.enabled:
            self.dashboard.start()
        self.state_manager.transition_to(AssistantState.IDLE)
        LOGGER.info("JARVIS bootstrap completed")

    def run_forever(self) -> None:
        self.bootstrap()
        try:
            while not self._shutdown.is_set():
                if self.wake_engine.wait_for_wake(timeout=0.3):
                    threading.Thread(
                        target=self._handle_command_cycle,
                        name="command-cycle",
                        daemon=True,
                    ).start()
        except KeyboardInterrupt:
            LOGGER.info("Shutdown requested by keyboard interrupt")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._shutdown.set()
        self.clap_detector.stop()
        self.audio_stream.stop()
        self.speech_engine.stop()
        self.calendar_watch.stop()
        self.task_engine.stop()
        self.dashboard.stop()
        self.system_actions.close()
        LOGGER.info("JARVIS services stopped")

    def _handle_command_cycle(self) -> None:
        if not self._command_lock.acquire(blocking=False):
            LOGGER.warning("Command cycle skipped due to active execution")
            return

        try:
            if self.state_manager.state != AssistantState.IDLE:
                return

            self.state_manager.transition_to(AssistantState.LISTENING)
            asr_timeout = self._config.voice.max_listen_seconds + 5.0
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.voice.listen_for_command)
                try:
                    spoken_text = future.result(timeout=asr_timeout)
                except concurrent.futures.TimeoutError:
                    LOGGER.error("ASR timed out after %.1f seconds", asr_timeout)
                    spoken_text = ""
            self.state_manager.set_last_command(spoken_text)

            if not spoken_text:
                response = "I did not catch any command."
                self._respond_and_reset(response)
                return

            self.state_manager.transition_to(AssistantState.PROCESSING)
            intent = self.intent_parser.parse(spoken_text)
            self.state_manager.set_last_intent(intent.name)

            self.state_manager.transition_to(AssistantState.EXECUTING)
            response = self._route_request(intent)
            self.memory_store.record_interaction(
                user_text=spoken_text,
                response_text=response,
                intent_name=intent.name,
                tool_name=self.state_manager.snapshot().last_tool,
                agent_mode=self.state_manager.snapshot().agent_mode,
            )
            self._respond_and_reset(response)
        finally:
            self._command_lock.release()

    def _respond_and_reset(self, response: str) -> None:
        self.state_manager.set_last_response(response)
        self.state_manager.transition_to(AssistantState.SPEAKING)
        self.speech_engine.speak(response)
        time.sleep(0.1)
        self.state_manager.transition_to(AssistantState.IDLE)

    def _execute_intent(self, intent: Intent) -> str:
        result = self.command_registry.dispatch(intent)
        if result.success:
            return result.message
        return f"Command failed: {result.message}"

    def _route_request(self, intent: Intent) -> str:
        if intent.name in {"UNKNOWN", "AGENT_REQUEST"}:
            query = intent.entities.get("query", intent.text) or intent.text
            return self._handle_agent_request(query)
        self.state_manager.set_agent_mode("deterministic")
        self.state_manager.set_last_tool("")
        return self._execute_intent(intent)

    def _handle_agent_request(self, user_text: str) -> str:
        self.state_manager.set_agent_mode("ollama")
        result = self._execute_agent_goal(user_text)
        self.state_manager.set_last_tool(result.tool_name)
        return result.response if result.success else f"Command failed: {result.response}"

    def _handle_open_app(self, intent: Intent) -> CommandResult:
        app_name = intent.entities.get("app", "")
        if not app_name:
            return CommandResult(False, "Missing app name.")
        success, message = self.system_actions.open_app(app_name).result(timeout=8)
        return CommandResult(success, message)

    def _register_builtin_commands(self) -> None:
        self.command_registry.register("OPEN_APP", self._handle_open_app)
        self.command_registry.register("LIST_APPS", self._handle_list_apps)
        self.command_registry.register("MEDIA_PLAY", self._handle_media_play)
        self.command_registry.register("MEDIA_PAUSE", self._handle_media_pause)
        self.command_registry.register("MEDIA_STOP", self._handle_media_stop)
        self.command_registry.register("FILE_READ", self._handle_file_read)
        self.command_registry.register("FILE_LIST", self._handle_file_list)
        self.command_registry.register("FILE_SEARCH", self._handle_file_search)
        self.command_registry.register("CALENDAR_UPCOMING", self._handle_calendar_upcoming)
        self.command_registry.register("CONTACT_SEARCH", self._handle_contact_search)
        self.command_registry.register("TASK_SUBMIT", self._handle_task_submit)
        self.command_registry.register("TASK_LIST", self._handle_task_list)
        self.command_registry.register("SYSTEM_TIME", self._handle_system_time)
        self.command_registry.register("SHUTDOWN_SYSTEM", self._handle_shutdown)
        self.command_registry.register("SYSTEM_CAPABILITIES", self._handle_capabilities)
        self.command_registry.register("SYSTEM_STATUS", self._handle_status)

    def _register_agent_tools(self) -> None:
        self.agent_orchestrator.register_tool(
            ToolDefinition("open_app", "Open a desktop application by name", {"app_name": "string"}),
            self._tool_open_app,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition(
                "focus_window",
                "Focus a desktop window by partial title match",
                {"window_name": "string"},
            ),
            self._tool_focus_window,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition(
                "type_text",
                "Type text into the active graphical window",
                {"text": "string"},
            ),
            self._tool_type_text,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition(
                "press_keys",
                "Press a keyboard shortcut on the active desktop session",
                {"keys": "array of strings"},
            ),
            self._tool_press_keys,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition("list_apps", "List known desktop applications", {}),
            self._tool_list_apps,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition("read_file", "Read a UTF-8 text file", {"path": "absolute or allowed relative path"}),
            self._tool_read_file,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition(
                "write_file",
                "Write UTF-8 text into a file inside allowed roots",
                {"path": "absolute or allowed relative path", "content": "string"},
            ),
            self._tool_write_file,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition("list_directory", "List files in a directory", {"path": "absolute or allowed relative path"}),
            self._tool_list_directory,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition(
                "search_files",
                "Search files using a wildcard pattern inside an allowed path",
                {"pattern": "*.py", "path": "absolute or allowed relative path"},
            ),
            self._tool_search_files,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition("calendar_upcoming", "Read upcoming Google Calendar events", {"max_results": "integer"}),
            self._tool_calendar_upcoming,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition("search_contacts", "Search Google contacts by name", {"query": "string"}),
            self._tool_search_contacts,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition("submit_task", "Queue a long-running autonomous task", {"goal": "string"}),
            self._tool_submit_task,
        )
        self.agent_orchestrator.register_tool(
            ToolDefinition("list_tasks", "List recently queued tasks and their statuses", {}),
            self._tool_list_tasks,
        )
        if not self._config.system.safe_mode:
            self.agent_orchestrator.register_tool(
                ToolDefinition("run_shell_command", "Execute a shell command on Linux", {"command": "string"}),
                self._tool_run_shell_command,
            )

    def _handle_media_play(self, _intent: Intent) -> CommandResult:
        success, message = self.media_actions.play()
        return CommandResult(success, message)

    def _handle_list_apps(self, _intent: Intent) -> CommandResult:
        success, message, _apps = self.system_actions.list_available_apps().result(timeout=10)
        return CommandResult(success, message)

    def _handle_file_read(self, intent: Intent) -> CommandResult:
        success, message, _content = self.file_actions.read_text_file(intent.entities.get("path", ""))
        return CommandResult(success, message if success else message)

    def _handle_file_list(self, intent: Intent) -> CommandResult:
        success, message, _entries = self.file_actions.list_directory(intent.entities.get("path", ""))
        return CommandResult(success, message)

    def _handle_file_search(self, intent: Intent) -> CommandResult:
        success, message, _matches = self.file_actions.search_files(
            pattern=intent.entities.get("pattern", "*"),
            base_path=intent.entities.get("path", "."),
        )
        return CommandResult(success, message)

    def _handle_calendar_upcoming(self, _intent: Intent) -> CommandResult:
        success, message, _events = self.google_workspace.upcoming_events()
        return CommandResult(success, message)

    def _handle_contact_search(self, intent: Intent) -> CommandResult:
        success, message, _contacts = self.google_workspace.search_contacts(intent.entities.get("query", ""))
        return CommandResult(success, message)

    def _handle_task_submit(self, intent: Intent) -> CommandResult:
        goal = intent.entities.get("goal", "").strip()
        if not goal:
            return CommandResult(False, "Missing task goal.")
        task_id = self.task_engine.submit(goal=goal, source="voice")
        return CommandResult(True, f"Queued task {task_id} for goal: {goal}")

    def _handle_task_list(self, _intent: Intent) -> CommandResult:
        tasks = self.task_engine.recent_tasks(limit=5)
        if not tasks:
            return CommandResult(True, "No tasks have been queued yet.")
        summary = "; ".join(f"{item['task_id'][:8]} {item['status']} {item['goal']}" for item in tasks)
        return CommandResult(True, f"Recent tasks: {summary}")

    def _handle_media_pause(self, _intent: Intent) -> CommandResult:
        success, message = self.media_actions.pause()
        return CommandResult(success, message)

    def _handle_media_stop(self, _intent: Intent) -> CommandResult:
        success, message = self.media_actions.stop()
        return CommandResult(success, message)

    def _handle_system_time(self, _intent: Intent) -> CommandResult:
        success, message = self.system_actions.get_time().result(timeout=5)
        return CommandResult(success, message)

    def _handle_shutdown(self, _intent: Intent) -> CommandResult:
        success, message = self.system_actions.shutdown_system().result(timeout=10)
        return CommandResult(success, message)

    def _handle_capabilities(self, _intent: Intent) -> CommandResult:
        success, message = self.system_actions.capabilities().result(timeout=5)
        return CommandResult(success, message)

    def _handle_status(self, _intent: Intent) -> CommandResult:
        success, message = self.system_actions.status().result(timeout=5)
        return CommandResult(success, message)

    def _build_agent_context(self) -> dict[str, str]:
        snapshot = self.state_manager.snapshot()
        return {
            "current_state": snapshot.state.value,
            "last_command": snapshot.last_command,
            "safe_mode": str(self._config.system.safe_mode),
            "allowed_roots": ", ".join(str(root) for root in self._config.filesystem.allowed_roots),
            "google_enabled": str(self._config.google.enabled),
            "ollama_model": self._config.ollama.model,
            "calendar_watch_enabled": str(self._config.scheduler.enable_calendar_watch),
            "planner_steps": str(self._config.agent.max_planning_steps),
            "recent_tasks": self._format_recent_tasks(),
            "recent_memory": self._format_recent_memory(),
        }

    def _format_recent_memory(self) -> str:
        recent = self.memory_store.recent_interactions(limit=6)
        if not recent:
            return "No stored interactions yet."
        lines = []
        for item in recent:
            lines.append(
                " | ".join(
                    [
                        f"user={item['user_text']}",
                        f"intent={item['intent_name']}",
                        f"tool={item['tool_name']}",
                        f"mode={item['agent_mode']}",
                    ]
                )
            )
        return " ; ".join(lines)

    def _tool_open_app(self, arguments: dict[str, object]) -> AgentExecutionResult:
        app_name = str(arguments.get("app_name", "")).strip()
        success, message = self.system_actions.open_app(app_name).result(timeout=10)
        return AgentExecutionResult(success=success, response=message, tool_name="open_app")

    def _tool_focus_window(self, arguments: dict[str, object]) -> AgentExecutionResult:
        window_name = str(arguments.get("window_name", "")).strip()
        success, message = self.desktop_actions.focus_window(window_name)
        return AgentExecutionResult(success=success, response=message, tool_name="focus_window")

    def _tool_type_text(self, arguments: dict[str, object]) -> AgentExecutionResult:
        text = str(arguments.get("text", ""))
        success, message = self.desktop_actions.type_text(text)
        return AgentExecutionResult(success=success, response=message, tool_name="type_text")

    def _tool_press_keys(self, arguments: dict[str, object]) -> AgentExecutionResult:
        raw_keys = arguments.get("keys", [])
        if isinstance(raw_keys, str):
            keys = [item.strip() for item in raw_keys.split("+") if item.strip()]
        elif isinstance(raw_keys, list):
            keys = [str(item).strip() for item in raw_keys if str(item).strip()]
        else:
            keys = []
        success, message = self.desktop_actions.press_keys(keys)
        return AgentExecutionResult(success=success, response=message, tool_name="press_keys")

    def _tool_list_apps(self, _arguments: dict[str, object]) -> AgentExecutionResult:
        success, message, apps = self.system_actions.list_available_apps().result(timeout=10)
        if success and apps:
            message = f"{message}. Total indexed apps: {len(apps)}."
        return AgentExecutionResult(success=success, response=message, tool_name="list_apps", details={"apps": apps})

    def _tool_read_file(self, arguments: dict[str, object]) -> AgentExecutionResult:
        path = str(arguments.get("path", "")).strip()
        success, message, content = self.file_actions.read_text_file(path)
        response = f"{message}\n\n{content}" if success and content else message
        return AgentExecutionResult(success=success, response=response, tool_name="read_file")

    def _tool_list_directory(self, arguments: dict[str, object]) -> AgentExecutionResult:
        path = str(arguments.get("path", ".")).strip() or "."
        success, message, entries = self.file_actions.list_directory(path)
        if success and entries:
            message = f"{message}. Total entries: {len(entries)}."
        return AgentExecutionResult(success=success, response=message, tool_name="list_directory")

    def _tool_write_file(self, arguments: dict[str, object]) -> AgentExecutionResult:
        path = str(arguments.get("path", "")).strip()
        content = str(arguments.get("content", ""))
        success, message = self.file_actions.write_text_file(path, content)
        return AgentExecutionResult(success=success, response=message, tool_name="write_file")

    def _tool_search_files(self, arguments: dict[str, object]) -> AgentExecutionResult:
        pattern = str(arguments.get("pattern", "*")).strip() or "*"
        path = str(arguments.get("path", ".")).strip() or "."
        success, message, matches = self.file_actions.search_files(pattern=pattern, base_path=path)
        if success and matches:
            message = f"{message}. Total matches: {len(matches)}."
        return AgentExecutionResult(success=success, response=message, tool_name="search_files")

    def _tool_calendar_upcoming(self, arguments: dict[str, object]) -> AgentExecutionResult:
        raw_max = arguments.get("max_results", 5)
        try:
            max_results = int(raw_max)
        except Exception:
            max_results = 5
        success, message, events = self.google_workspace.upcoming_events(max_results=max_results)
        return AgentExecutionResult(success=success, response=message, tool_name="calendar_upcoming", details={"events": events})

    def _tool_search_contacts(self, arguments: dict[str, object]) -> AgentExecutionResult:
        query = str(arguments.get("query", "")).strip()
        success, message, contacts = self.google_workspace.search_contacts(query=query)
        return AgentExecutionResult(success=success, response=message, tool_name="search_contacts", details={"contacts": contacts})

    def _tool_submit_task(self, arguments: dict[str, object]) -> AgentExecutionResult:
        goal = str(arguments.get("goal", "")).strip()
        if not goal:
            return AgentExecutionResult(success=False, response="Missing task goal.", tool_name="submit_task")
        task_id = self.task_engine.submit(goal=goal, source="agent")
        return AgentExecutionResult(
            success=True,
            response=f"Queued task {task_id} for goal: {goal}",
            tool_name="submit_task",
            details={"task_id": task_id},
        )

    def _tool_list_tasks(self, _arguments: dict[str, object]) -> AgentExecutionResult:
        tasks = self.task_engine.recent_tasks(limit=8)
        if not tasks:
            return AgentExecutionResult(success=True, response="No tasks have been queued yet.", tool_name="list_tasks")
        summary = "; ".join(f"{item['task_id'][:8]} {item['status']} {item['goal']}" for item in tasks)
        return AgentExecutionResult(success=True, response=f"Recent tasks: {summary}", tool_name="list_tasks")

    def _tool_run_shell_command(self, arguments: dict[str, object]) -> AgentExecutionResult:
        command = str(arguments.get("command", "")).strip()
        success, message = self.system_actions.execute_shell_command(command).result(timeout=40)
        return AgentExecutionResult(success=success, response=message, tool_name="run_shell_command")

    def _execute_agent_goal(self, user_text: str) -> AgentExecutionResult:
        return self.agent_orchestrator.handle(user_text=user_text, system_context=self._build_agent_context())

    def _format_recent_tasks(self) -> str:
        tasks = self.task_engine.recent_tasks(limit=5)
        if not tasks:
            return "No queued tasks."
        return " ; ".join(f"{item['task_id'][:8]}:{item['status']}:{item['goal']}" for item in tasks)

    def _on_task_update(self, task_id: str) -> None:
        task = self.task_engine.get_task(task_id)
        if task is None:
            return
        self.state_manager.set_active_task(task_id=task["task_id"], status=task["status"])
        self.state_manager.add_history_entry(
            f"TASK: {task['task_id'][:8]} {task['status']} {task['goal']}"
        )
        if task["status"] == "COMPLETED" and task["result_text"]:
            self.speech_engine.speak(f"Task completed. {task['result_text']}")
        elif task["status"] == "FAILED" and task["last_error"]:
            self.speech_engine.speak(f"Task failed. {task['last_error']}")

    def _handle_background_reminder(self, message: str) -> None:
        self.state_manager.add_history_entry(f"REMINDER: {message}")
        self.speech_engine.speak(message)
