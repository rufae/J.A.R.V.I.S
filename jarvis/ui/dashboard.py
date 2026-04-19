from __future__ import annotations

import logging
import threading
import time
from typing import Any

from jarvis.ui.ui_state_bridge import UIStateBridge


LOGGER = logging.getLogger(__name__)


class DashboardServer:
    def __init__(self, host: str, port: int, bridge: UIStateBridge) -> None:
        self._host = host
        self._port = port
        self._bridge = bridge
        self._thread: threading.Thread | None = None
        self._server_thread: threading.Thread | None = None
        self._running = threading.Event()
        self._socketio: Any | None = None
        self._flask_app: Any | None = None

    def start(self) -> None:
        if self._running.is_set():
            return
        if not self._bootstrap_server():
            return

        self._running.set()
        self._thread = threading.Thread(target=self._emit_loop, name="ui-emitter", daemon=True)
        self._thread.start()
        self._server_thread = threading.Thread(target=self._run_server, name="ui-server", daemon=True)
        self._server_thread.start()

        LOGGER.info("Dashboard available at http://%s:%s", self._host, self._port)

    def stop(self) -> None:
        self._running.clear()

    def _bootstrap_server(self) -> bool:
        try:
            from flask import Flask
            from flask_socketio import SocketIO
        except Exception:
            LOGGER.exception("Flask/SocketIO import failed")
            return False

        app = Flask(__name__)
        socketio = SocketIO(app, cors_allowed_origins="*")

        @app.get("/")
        def index() -> str:
            return _build_html()

        @socketio.on("connect")
        def on_connect() -> None:
            socketio.emit("state_update", self._bridge.current_state())

        self._flask_app = app
        self._socketio = socketio
        return True

    def _emit_loop(self) -> None:
        while self._running.is_set():
            if self._socketio is not None:
                self._socketio.emit("state_update", self._bridge.current_state())
            time.sleep(0.25)

    def _run_server(self) -> None:
        if self._socketio is None or self._flask_app is None:
            return
        self._socketio.run(
            self._flask_app,
            host=self._host,
            port=self._port,
            allow_unsafe_werkzeug=True,
        )


def _build_html() -> str:
    return """
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>JARVIS Dashboard</title>
  <style>
    :root {
      --bg: #071016;
      --panel: #0d1f2b;
      --accent: #00d4ff;
      --accent-soft: rgba(0, 212, 255, 0.25);
      --text: #d7f3ff;
      --muted: #7eb0bf;
      --danger: #ff5f5f;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 20% 20%, #123043 0%, transparent 40%),
        radial-gradient(circle at 80% 0%, #102a3a 0%, transparent 45%),
        var(--bg);
      color: var(--text);
      font-family: "Space Mono", "JetBrains Mono", monospace;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 18px;
    }
    .grid {
      width: min(960px, 100%);
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }
    .card {
      background: linear-gradient(180deg, rgba(255,255,255,0.02), transparent), var(--panel);
      border: 1px solid var(--accent-soft);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 0 35px rgba(0, 60, 90, 0.25);
    }
    h1 { margin: 0; font-size: 1.15rem; letter-spacing: 0.08em; }
    .row {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 10px;
      margin-top: 10px;
      align-items: center;
    }
    .state {
      padding: 6px 12px;
      border: 1px solid var(--accent-soft);
      border-radius: 999px;
      letter-spacing: 0.08em;
    }
    .pulse {
      width: 14px;
      height: 14px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 0 0 var(--accent-soft);
      animation: pulse 1.2s infinite;
    }
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(0, 212, 255, 0.6); }
      70% { box-shadow: 0 0 0 15px rgba(0, 212, 255, 0); }
      100% { box-shadow: 0 0 0 0 rgba(0, 212, 255, 0); }
    }
    .label { color: var(--muted); font-size: 0.85rem; }
    .value { margin-top: 4px; }
    .history {
      max-height: 260px;
      overflow: auto;
      border: 1px solid rgba(126,176,191,0.25);
      border-radius: 10px;
      padding: 10px;
      font-size: 0.86rem;
      line-height: 1.35;
      background: rgba(5, 18, 28, 0.45);
    }
    .meter {
      height: 8px;
      border-radius: 99px;
      background: rgba(126,176,191,0.2);
      overflow: hidden;
      margin-top: 10px;
    }
    .meter > div {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, #00f0ff, #72ffe2);
      transition: width 90ms linear;
    }
  </style>
</head>
<body>
  <main class=\"grid\">
    <section class=\"card\">
      <h1>JARVIS CONTROL GRID</h1>
      <div class=\"row\">
      <div class="label" style="margin-top:12px">Active task</div>
      <div class="value" id="task">-</div>
      <div class="label" style="margin-top:12px">Task status</div>
      <div class="value" id="task_status">-</div>
      <div class="label" style="margin-top:12px">Last intent</div>
      <div class="value" id="intent">-</div>
      <div class="label" style="margin-top:12px">Agent mode</div>
      <div class="value" id="agent_mode">deterministic</div>
      <div class="label" style="margin-top:12px">Last tool</div>
      <div class="value" id="tool">-</div>
        <div class=\"state\" id=\"state\">IDLE</div>
        <div class=\"pulse\"></div>
      </div>
      <div class=\"meter\"><div id=\"mic\"></div></div>
    </section>
    <section class=\"card\">
      <div class=\"label\">Last command</div>
      <div class=\"value\" id=\"command\">-</div>
      <div class=\"label\" style=\"margin-top:12px\">Last response</div>
      <div class=\"value\" id=\"response\">-</div>
    </section>
    <section class=\"card\">
      <div class=\"label\">History</div>
      <div class=\"history\" id=\"history\"></div>
    </section>
  </main>

  <script src=\"/socket.io/socket.io.js\"></script>
  <script>
    const socket = io();
    const stateEl = document.getElementById("state");
    const cmdEl = document.getElementById("command");
    const taskEl = document.getElementById("task");
    const taskStatusEl = document.getElementById("task_status");
    const intentEl = document.getElementById("intent");
    const agentModeEl = document.getElementById("agent_mode");
    const toolEl = document.getElementById("tool");
    const rspEl = document.getElementById("response");
    const micEl = document.getElementById("mic");
    const historyEl = document.getElementById("history");

    socket.on("state_update", (payload) => {
      stateEl.textContent = payload.state || "IDLE";
      cmdEl.textContent = payload.last_command || "-";
      taskEl.textContent = payload.active_task_id || "-";
      taskStatusEl.textContent = payload.active_task_status || "-";
      intentEl.textContent = payload.last_intent || "-";
      agentModeEl.textContent = payload.agent_mode || "deterministic";
      toolEl.textContent = payload.last_tool || "-";
      rspEl.textContent = payload.last_response || "-";
      const mic = Math.max(0, Math.min(1, Number(payload.mic_level || 0)));
      micEl.style.width = `${Math.round(mic * 100)}%`;
      const history = Array.isArray(payload.history) ? payload.history : [];
      historyEl.textContent = history.slice(-20).join("\\n");
      historyEl.scrollTop = historyEl.scrollHeight;
    });
  </script>
</body>
</html>
    """
