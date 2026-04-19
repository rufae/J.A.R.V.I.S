from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass()
class ToolDefinition:
    name: str
    description: str
    arguments: dict[str, str] = field(default_factory=dict)


@dataclass()
class AgentDecision:
    mode: str
    response: str = ""
    tool_name: str = ""
    tool_arguments: dict[str, Any] = field(default_factory=dict)
    thought: str = ""


@dataclass()
class AgentExecutionResult:
    success: bool
    response: str
    tool_name: str = ""
    details: dict[str, Any] = field(default_factory=dict)
