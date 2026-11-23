from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from jarvis.agent.models import AgentDecision, ToolDefinition
from jarvis.core.config import OllamaConfig

LOGGER = logging.getLogger(__name__)


class OllamaBrain:
    def __init__(self, config: OllamaConfig) -> None:
        self._config = config

    @property
    def is_enabled(self) -> bool:
        return bool(self._config.enabled and self._config.base_url and self._config.model)

    def decide(
        self,
        user_text: str,
        tools: list[ToolDefinition],
        system_context: dict[str, str],
    ) -> AgentDecision:
        if not self.is_enabled:
            return AgentDecision(mode="reply", response="Local agent brain is not enabled.")

        prompt = self._build_prompt(user_text=user_text, tools=tools, system_context=system_context)
        payload = {
            "model": self._config.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self._config.temperature,
            },
        }

        try:
            body = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                url=f"{self._config.base_url.rstrip('/')}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self._config.timeout_seconds) as response:
                raw_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError:
            LOGGER.exception("Ollama request failed")
            return AgentDecision(mode="reply", response="I cannot reach the local Ollama service.")
        except Exception:
            LOGGER.exception("Unexpected Ollama failure")
            return AgentDecision(
                mode="reply",
                response="The local AI brain failed to process the request.",
            )

        return self._parse_response(raw_payload.get("response", ""))

    def _build_prompt(
        self,
        user_text: str,
        tools: list[ToolDefinition],
        system_context: dict[str, str],
    ) -> str:
        tool_lines = []
        for tool in tools:
            arguments = ", ".join(f"{key}: {value}" for key, value in tool.arguments.items())
            tool_lines.append(f"- {tool.name}: {tool.description}. args={{ {arguments} }}")

        context_lines = [f"- {key}: {value}" for key, value in system_context.items()]

        return (
            "You are JARVIS, a local Linux AI agent running 24/7. "
            "You must respond only with valid JSON and choose exactly one action.\n\n"
            "JSON schema:\n"
            '{"mode":"reply|tool","response":"string","tool_name":"string","tool_arguments":{},"thought":"string"}\n\n'
            "Rules:\n"
            "- Use mode=tool when a tool can answer or execute the request.\n"
            "- Use mode=reply only for conversational answers or when no tool fits.\n"
            "- If previous tool results are present, use them to continue the plan "
            "or produce the final answer.\n"
            "- Never invent tool names.\n"
            "- Keep response concise and operational.\n\n"
            "System context:\n"
            + "\n".join(context_lines)
            + "\n\nAvailable tools:\n"
            + "\n".join(tool_lines)
            + "\n\nUser request:\n"
            + user_text
        )

    def _parse_response(self, response_text: str) -> AgentDecision:
        try:
            payload = json.loads(response_text)
        except Exception:
            LOGGER.warning("Ollama returned non-JSON response")
            return AgentDecision(
                mode="reply",
                response=response_text.strip() or "I could not parse the AI response.",
            )

        mode = str(payload.get("mode", "reply")).strip().lower() or "reply"
        response = str(payload.get("response", "")).strip()
        tool_name = str(payload.get("tool_name", "")).strip()
        tool_arguments = payload.get("tool_arguments", {})
        if not isinstance(tool_arguments, dict):
            tool_arguments = {}

        return AgentDecision(
            mode=mode,
            response=response,
            tool_name=tool_name,
            tool_arguments=tool_arguments,
            thought=str(payload.get("thought", "")).strip(),
        )
