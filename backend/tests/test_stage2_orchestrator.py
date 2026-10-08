import pytest
from sqlalchemy.orm import Session
from app.agents.orchestrator_agent import OrchestratorAgent
from app.models.all_models import AgentActivity


def test_orchestrator_groq_missing_guard(monkeypatch):
    """Verify OrchestratorAgent returns explicit ERROR if GROQ_API_KEY is missing."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr("app.core.config.settings.GROQ_API_KEY", None)
    orchestrator = OrchestratorAgent()
    res = orchestrator.run("Diwali is in 10 days, prep the Mumbai warehouse", context={})
    assert res["status"] == "ERROR"
    assert "GROQ_API_KEY is missing" in res["error"]



def test_orchestrator_registered_tools():
    """Verify OrchestratorAgent registers all 5 sub-agent execution tools."""
    orchestrator = OrchestratorAgent()
    tool_names = [schema["function"]["name"] for schema in orchestrator._tool_schemas]
    assert "run_data_agent" in tool_names
    assert "run_forecast_agent" in tool_names
    assert "run_inventory_agent" in tool_names
    assert "run_wastage_agent" in tool_names
    assert "run_route_agent" in tool_names
