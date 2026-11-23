from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from jarvis.agent.brain import OllamaBrain
from jarvis.agent.models import AgentDecision, AgentExecutionResult, ToolDefinition
from jarvis.agent.planner import AgentPlanner

LOGGER = logging.getLogger(__name__)


ToolHandler = Callable[[dict[str, Any]], AgentExecutionResult]


class AgentOrchestrator:
    def __init__(self, brain: OllamaBrain, planner: AgentPlanner | None = None) -> None:
        self._brain = brain
        self._planner = planner or AgentPlanner(brain)
        self._tools: dict[str, tuple[ToolDefinition, ToolHandler]] = {}

    def register_tool(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        self._tools[definition.name] = (definition, handler)

    def available_tools(self) -> list[ToolDefinition]:
        return [item[0] for item in self._tools.values()]

    def handle(self, user_text: str, system_context: dict[str, str]) -> AgentExecutionResult:
        return self._planner.plan(
            user_text=user_text,
            tools=self.available_tools(),
            system_context=system_context,
            executor=self._execute_decision,
        )

    def _execute_decision(self, decision: AgentDecision) -> AgentExecutionResult:
        if decision.mode != "tool":
            return AgentExecutionResult(
                success=True,
                response=decision.response or "No tool execution required.",
            )

        target = self._tools.get(decision.tool_name)
        if target is None:
            return AgentExecutionResult(
                success=False, response="The selected tool is not registered."
            )

        _definition, handler = target
        try:
            result = handler(decision.tool_arguments)
        except Exception:
            LOGGER.exception("Agent tool execution failed for %s", decision.tool_name)
            return AgentExecutionResult(
                success=False,
                response="The agent tool execution failed.",
                tool_name=decision.tool_name,
            )

        if not result.tool_name:
            result.tool_name = decision.tool_name
        return result
