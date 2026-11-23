"""Tests de los modelos de datos del agente (dataclasses)."""

from jarvis.agent.models import AgentDecision, AgentExecutionResult, ToolDefinition


def test_tool_definition_defaults():
    tool = ToolDefinition(name="open_app", description="Opens an application")
    assert tool.arguments == {}
    assert tool.name == "open_app"


def test_agent_decision_defaults():
    decision = AgentDecision(mode="tool", tool_name="open_app")
    assert decision.response == ""
    assert decision.tool_arguments == {}
    assert decision.thought == ""


def test_execution_result_carries_details():
    result = AgentExecutionResult(
        success=True, response="done", tool_name="open_app", details={"app": "firefox"}
    )
    assert result.success is True
    assert result.details["app"] == "firefox"
