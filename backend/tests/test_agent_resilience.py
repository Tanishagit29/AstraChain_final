"""
Regression tests for the Groq integration.

Bug being guarded against: after Groq was added, the CSV upload pipeline ran LLM agents inside the HTTP request.
A slow / rate-limited / failing LLM froze the whole API, so the pipeline returned nothing and no page loaded.
"""
import io
import json
from types import SimpleNamespace as NS

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.agents import base_agent
from app.agents.base_agent import (
    llm_breaker,
    coerce_tool_args,
    serialize_tool_result,
    MAX_TOOL_RESULT_CHARS,
)
from app.agents.inventory_agent import InventoryAgent
from app.services.pipeline_state import pipeline_state
from app.services import agent_insights

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_breaker():
    llm_breaker.reset()
    yield
    llm_breaker.reset()


def _csv_upload():
    df = pd.DataFrame({
        "product_id": ["SKU-A", "SKU-B", "SKU-C"],
        "product_name": ["Milk", "Cheese", "Bread"],
        "category": ["Dairy", "Dairy", "Bakery"],
        "current_stock": [10, 500, 80],
        "demand": [200, 100, 100],
        "unit_cost": ["₹70", "₹140", "₹40"],
        "expiry_date": ["2030-01-01", "2030-01-01", "2030-01-01"],
    })
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return [("files", ("resilience.csv", buf.getvalue(), "text/csv"))]


class ExplodingClient:
    """Fails the test if anything tries to reach the LLM."""
    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                raise AssertionError("LLM was called inside the upload pipeline")


def test_pipeline_never_waits_on_llm(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    monkeypatch.setattr(base_agent, "make_groq_client", lambda: ExplodingClient())
    # Don't start the background insight thread in this test; we only check the request path.
    monkeypatch.setattr("app.api.routes.data_collection.launch_agent_insights", lambda **kw: None)

    res = client.post("/api/data-collection/pipeline", files=_csv_upload())
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "success"
    assert all(v == "completed" for v in body["stages"].values())

    for path in ("/api/pipeline/dashboard", "/api/pipeline/forecast", "/api/pipeline/inventory", "/api/pipeline/wastage"):
        assert client.get(path).json()["has_data"] is True, path


def test_llm_failure_trips_breaker_and_falls_back(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    calls = {"n": 0}

    class FailingClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    calls["n"] += 1
                    raise ConnectionError("simulated Groq outage")

    monkeypatch.setattr(base_agent, "make_groq_client", lambda: FailingClient())

    res = InventoryAgent().run(task="check stock", context={"db": None})
    assert res["status"] == "FALLBACK"
    assert llm_breaker.is_open()
    assert calls["n"] == 1

    # A second agent must not wait on the dead LLM again.
    InventoryAgent().run(task="check stock again", context={"db": None})
    assert calls["n"] == 1


def test_tool_format_errors_do_not_trip_breaker(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")

    class BadToolClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("Error code: 400 - tool_use_failed: Failed to call a function")

    monkeypatch.setattr(base_agent, "make_groq_client", lambda: BadToolClient())
    res = InventoryAgent().run(task="check stock", context={"db": None})
    assert res["status"] == "FALLBACK"
    assert not llm_breaker.is_open()


def test_coerce_tool_args_cleans_llm_output():
    schema = {"function": {"parameters": {"properties": {
        "product_id": {"type": "string"},
        "horizon_days": {"type": "integer"},
        "discount_pct": {"type": "number"},
    }}}}
    cleaned = coerce_tool_args(schema, {
        "product_id": 123,
        "horizon_days": "30",
        "discount_pct": "12.5",
        "made_up": "x",
        "none_value": None,
    })
    assert cleaned == {"product_id": "123", "horizon_days": 30, "discount_pct": 12.5}
    assert coerce_tool_args(schema, "not a dict") == {}


def test_tool_results_are_capped():
    huge = {"items": [{"name": f"item-{i}", "blob": "x" * 200} for i in range(500)]}
    text = serialize_tool_result(huge)
    assert len(text) <= MAX_TOOL_RESULT_CHARS + 50
    assert "item-0" in text


def test_agent_insights_skipped_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(base_agent.settings, "GROQ_API_KEY", None)

    res = client.post("/api/data-collection/pipeline", files=_csv_upload())
    assert res.status_code == 200, res.text

    ins = client.get("/api/pipeline/agents").json()
    assert ins["status"] == "skipped"
    assert "GROQ_API_KEY" in ins["message"]


def test_agent_insights_run_with_llm(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")

    class ScriptedCompletions:
        @staticmethod
        def create(**kwargs):
            msgs = kwargs["messages"]
            if msgs[-1]["role"] == "tool":
                return NS(choices=[NS(message=NS(content="Analysis complete.", tool_calls=None))])
            names = {t["function"]["name"] for t in kwargs.get("tools") or []}
            first = next(
                (n for n in ("generate_xgboost_forecast", "evaluate_inventory_risk", "get_near_expiry_items") if n in names),
                None,
            )
            args = {"product_id": "SKU-A", "horizon_days": "30"} if first == "generate_xgboost_forecast" else {}
            tc = NS(id="call_1", type="function", function=NS(name=first, arguments=json.dumps(args)))
            return NS(choices=[NS(message=NS(content=None, tool_calls=[tc]))])

    monkeypatch.setattr(base_agent, "make_groq_client", lambda: NS(chat=NS(completions=ScriptedCompletions())))
    monkeypatch.setattr("app.api.routes.data_collection.launch_agent_insights", lambda **kw: None)

    assert client.post("/api/data-collection/pipeline", files=_csv_upload()).status_code == 200

    agent_insights.run_agent_insights(pipeline_state.dataset_id, "SKU-A")
    ins = client.get("/api/pipeline/agents").json()
    assert ins["status"] == "completed"
    assert [a["mode"] for a in ins["agents"]] == ["llm", "llm", "llm"]
    assert ins["agents"][0]["tools_used"] == ["generate_xgboost_forecast"]
