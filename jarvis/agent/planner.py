from __future__ import annotations

import logging
from dataclasses import dataclass, field

from jarvis.agent.brain import OllamaBrain
from jarvis.agent.models import AgentExecutionResult, ToolDefinition

LOGGER = logging.getLogger(__name__)


@dataclass()
class PlannerStep:
    tool_name: str
    summary: str


@dataclass()
class PlannerTrace:
    steps: list[PlannerStep] = field(default_factory=list)

    def add(self, tool_name: str, summary: str) -> None:
        self.steps.append(PlannerStep(tool_name=tool_name, summary=summary[:1000]))

    def to_prompt(self) -> str:
        if not self.steps:
            return "No previous tool executions."
        return "\n".join(f"- {step.tool_name}: {step.summary}" for step in self.steps)


class AgentPlanner:
    def __init__(self, brain: OllamaBrain, max_steps: int = 4) -> None:
        self._brain = brain
        self._max_steps = max_steps

    @property
    def max_steps(self) -> int:
        return self._max_steps

    def plan(
        self,
        user_text: str,
        tools: list[ToolDefinition],
        system_context: dict[str, str],
        executor,
    ) -> AgentExecutionResult:
        trace = PlannerTrace()
        last_result: AgentExecutionResult | None = None

        for _index in range(self._max_steps):
            decision = self._brain.decide(
                user_text=user_text,
                tools=tools,
                system_context={**system_context, "execution_trace": trace.to_prompt()},
            )

            if decision.mode != "tool":
                if decision.response:
                    return AgentExecutionResult(success=True, response=decision.response)
                if last_result is not None:
                    return last_result
                return AgentExecutionResult(
                    success=False,
                    response="The planner did not produce a final response.",
                )

            result = executor(decision)
            trace.add(result.tool_name or decision.tool_name, result.response)
            last_result = result

            if not result.success:
                return result

        if last_result is not None:
            return AgentExecutionResult(
                success=True,
                response=last_result.response,
                tool_name=last_result.tool_name,
                details=last_result.details,
            )
        return AgentExecutionResult(
            success=False, response="Planner exceeded the maximum number of steps."
        )
