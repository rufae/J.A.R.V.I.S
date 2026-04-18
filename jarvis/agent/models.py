from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    arguments: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AgentDecision:
    mode: str
    response: str = ""
    tool_name: str = ""
    tool_arguments: dict[str, Any] = field(default_factory=dict)
    thought: str = ""


@dataclass(slots=True)
class AgentExecutionResult:
    success: bool
    response: str
    tool_name: str = ""
    details: dict[str, Any] = field(default_factory=dict)
