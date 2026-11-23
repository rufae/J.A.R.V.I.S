"""Tests del planificador del agente (trazas y límite de pasos)."""

from jarvis.agent.planner import AgentPlanner, PlannerTrace


def test_trace_add_and_prompt():
    trace = PlannerTrace()
    trace.add("open_app", "abre firefox")
    trace.add("file_read", "lee notas")
    prompt = trace.to_prompt()
    assert "open_app" in prompt
    assert "abre firefox" in prompt
    assert "file_read" in prompt


def test_empty_trace_prompt_is_harmless():
    assert isinstance(PlannerTrace().to_prompt(), str)


def test_planner_respects_max_steps():
    class FakeBrain:
        pass

    planner = AgentPlanner(FakeBrain(), max_steps=3)
    assert planner.max_steps == 3
    planner2 = AgentPlanner(FakeBrain())
    assert planner2.max_steps == 4
