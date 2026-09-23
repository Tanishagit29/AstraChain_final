import json
import pytest
from app.agents.wastage_agent import WastageAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.models.all_models import AutomationLog, ConversationHistory
from app.services.ai_service import AIService
from app.schemas.ai import AIChatRequest


class MockFunctionCall:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class MockToolCall:
    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.type = "function"
        self.function = MockFunctionCall(name, arguments)


class MockMessage:
    def __init__(self, content: str = None, tool_calls: list = None):
        self.content = content
        self.tool_calls = tool_calls


class MockChoice:
    def __init__(self, message: MockMessage):
        self.message = message


class MockCompletionResponse:
    def __init__(self, message: MockMessage):
        self.choices = [MockChoice(message)]


def test_react_loop_tool_execution(monkeypatch, db_session):
    """
    (a) Test that the ReAct loop terminates and executes the right tool for a given scenario.
    """
    agent = WastageAgent()
    monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

    responses = [
        # Step 1: LLM returns tool_call to apply_discount
        MockCompletionResponse(
            MockMessage(
                content=None,
                tool_calls=[
                    MockToolCall(
                        id="call_001",
                        name="apply_discount",
                        arguments=json.dumps({
                            "batch_id": "WS-401",
                            "discount_pct": 25,
                            "reasoning": "Batch WS-401 has 120L at risk with cold chain variance; 25% promo recommended."
                        })
                    )
                ]
            )
        ),
        # Step 2: LLM produces final answer
        MockCompletionResponse(
            MockMessage(content="Dynamic markdown recommendation of 25% applied to batch WS-401.")
        )
    ]

    call_count = 0

    def mock_create(*args, **kwargs):
        nonlocal call_count
        resp = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    monkeypatch.setattr(agent, "_call_groq_with_retry", mock_create)
    # Ensure _get_groq_client returns a dummy non-None object
    monkeypatch.setattr(agent, "_get_groq_client", lambda: object())

    res = agent.run(task="Evaluate batch WS-401 for wastage risk", context={"db": db_session})

    assert res["status"] == "SUCCESS"
    assert res["steps"] == 2
    assert len(res["tools_executed"]) == 1
    assert res["tools_executed"][0]["tool"] == "apply_discount"
    assert res["tools_executed"][0]["arguments"]["batch_id"] == "WS-401"
    assert res["tools_executed"][0]["arguments"]["discount_pct"] == 25

    # Verify persistent DB entry
    log_entry = db_session.query(AutomationLog).filter(AutomationLog.rule_code == "AUT-DISCOUNT-WS-401").first()
    assert log_entry is not None
    assert "LLM Reasoning: Batch WS-401" in log_entry.trigger
    assert log_entry.status == "PENDING_APPROVAL"


def test_orchestrator_agent_skips_irrelevant_agents(monkeypatch, db_session):
    """
    (b) Test that the orchestrator skips agents that aren't relevant to a given task.
    """
    orchestrator = OrchestratorAgent()
    monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

    responses = [
        # Step 1: LLM decides to call ONLY run_forecast_agent, skipping route/wastage/inventory
        MockCompletionResponse(
            MockMessage(
                content=None,
                tool_calls=[
                    MockToolCall(
                        id="call_orch_1",
                        name="run_forecast_agent",
                        arguments=json.dumps({
                            "product_id": "MK-001-F",
                            "horizon_days": 30
                        })
                    )
                ]
            )
        ),
        # Step 2: Final synthesized answer
        MockCompletionResponse(
            MockMessage(content="Completed 30-day forecast for MK-001-F.")
        )
    ]

    call_count = 0

    def mock_create(*args, **kwargs):
        nonlocal call_count
        resp = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    monkeypatch.setattr(orchestrator, "_call_groq_with_retry", mock_create)
    monkeypatch.setattr(orchestrator, "_get_groq_client", lambda: object())

    task_str = "Generate XGBoost demand forecast for Fresh Milk MK-001-F for next 30 days."
    res = orchestrator.run(task=task_str, context={"db": db_session})

    assert res["status"] == "SUCCESS"
    tools_called = [t["tool"] for t in res["tools_executed"]]
    assert "run_forecast_agent" in tools_called
    assert "run_route_agent" not in tools_called
    assert "run_wastage_agent" not in tools_called


def test_request_expedited_route_tool_selection(monkeypatch, db_session):
    """
    (c) Test that request_expedited_route is only called when mocked tool_calls include it (agent decision test).
    """
    agent = WastageAgent()
    monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")

    responses = [
        # Step 1: LLM selects request_expedited_route due to high batch value
        MockCompletionResponse(
            MockMessage(
                content=None,
                tool_calls=[
                    MockToolCall(
                        id="call_route_1",
                        name="request_expedited_route",
                        arguments=json.dumps({
                            "batch_id": "WS-402",
                            "destination": "Pune Logistics Hub"
                        })
                    )
                ]
            )
        ),
        # Step 2: Final response
        MockCompletionResponse(
            MockMessage(content="Dispatched expedited transit for WS-402 to Pune Logistics Hub.")
        )
    ]

    call_count = 0

    def mock_create(*args, **kwargs):
        nonlocal call_count
        resp = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    monkeypatch.setattr(agent, "_call_groq_with_retry", mock_create)
    monkeypatch.setattr(agent, "_get_groq_client", lambda: object())

    res = agent.run(task="High value strawberry batch WS-402 is near expiry; assess rerouting.", context={"db": db_session})

    assert res["status"] == "SUCCESS"
    assert len(res["tools_executed"]) == 1
    assert res["tools_executed"][0]["tool"] == "request_expedited_route"
    assert res["tools_executed"][0]["arguments"]["destination"] == "Pune Logistics Hub"

    # Verify AutomationLog entry created for handoff
    log_entry = db_session.query(AutomationLog).filter(AutomationLog.rule_code == "AUT-REROUTE-WS-402").first()
    assert log_entry is not None
    assert "Expedited Reroute Handoff" in log_entry.name


def test_groq_fallback_when_key_absent(monkeypatch, db_session):
    """
    (d) Test that the fallback path works gracefully when GROQ_API_KEY is absent.
    """
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr("app.core.config.settings.GROQ_API_KEY", None)

    agent = WastageAgent()
    res = agent.execute(db_session)

    assert res["status"] == "FALLBACK"
    assert "discount_alerts" in res
    assert "waste_stats" in res
    assert res["discount_alerts_count"] >= 0


def test_orchestrator_endpoint(client):
    """
    Test POST /api/multi-agent/orchestrate API endpoint.
    """
    res = client.post("/api/multi-agent/orchestrate", json={"task": "Check perishable wastage and low stock"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "summary" in data
    assert "tools_executed" in data


def test_copilot_chat_history_persistence(client, db_session):
    """
    Test session conversation history persistence in AIService process_chat.
    """
    session_id = "test-session-101"
    req = AIChatRequest(message="What is the stock status of Fresh Milk?", session_id=session_id)
    resp = AIService.process_chat(db_session, req)

    assert resp.reply is not None

    # Check ConversationHistory table entries
    history_entries = (
        db_session.query(ConversationHistory)
        .filter(ConversationHistory.session_id == session_id)
        .all()
    )
    assert len(history_entries) == 2
    assert history_entries[0].role == "user"
    assert history_entries[0].content == "What is the stock status of Fresh Milk?"
    assert history_entries[1].role == "assistant"
