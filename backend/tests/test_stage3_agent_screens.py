import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models import all_models
from app.models.all_models import AgentActivity
from app.main import app
from app.database.session import get_db
from app.services.pipeline_state import pipeline_state

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_stage3.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db_stage3():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db_stage3
    db = TestingSessionLocal()
    if db.query(AgentActivity).count() == 0:
        db.add(AgentActivity(
            agent_code="AG-01",
            agent="Demand & Forecasting Agent",
            role="Predictive Analytics",
            status="ACTIVE",
            confidence="96%",
            tasks_processed=10,
            latency="14ms",
            action="Generated XGBoost forecast",
            details="Forecast generated for MK-001-F",
            time_ago="Just now",
            color="primary"
        ))
        db.commit()
    db.close()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os
    if os.path.exists("./test_stage3.db"):
        try:
            os.remove("./test_stage3.db")
        except Exception:
            pass


def test_pipeline_dashboard_returns_agent_traces_and_activities():
    """Verify /pipeline/dashboard returns agent activities and execution traces."""
    pipeline_state.start_pipeline()
    pipeline_state.add_agent_trace(
        agent_id="AG-DATA",
        agent_name="Data Agent",
        task="Clean file",
        reasoning_steps=["Mapped columns", "Validated schema"],
        tools_executed=[{"tool": "map_columns"}]
    )
    
    response = client.get("/api/pipeline/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["has_data"] is True
    assert "agent_activities" in data
    assert "agent_traces" in data
    assert len(data["agent_activities"]) > 0
    assert len(data["agent_traces"]) > 0
    assert any(t["agent_id"] == "AG-DATA" for t in data["agent_traces"])


def test_pipeline_sub_screens_return_agent_traces():
    """Verify /pipeline/forecast, /inventory, /wastage return filtered agent traces."""
    pipeline_state.start_pipeline()
    pipeline_state.add_agent_trace("AG-01", "Forecast Agent", "Run forecast", ["Step 1"], [])
    pipeline_state.add_agent_trace("AG-02", "Inventory Agent", "Run inventory risk", ["Step 1"], [])
    pipeline_state.add_agent_trace("AG-03", "Wastage Agent", "Run wastage markdown", ["Step 1"], [])

    res_f = client.get("/api/pipeline/forecast")
    assert res_f.status_code == 200
    assert "agent_traces" in res_f.json()
    assert any(t["agent_id"] == "AG-01" for t in res_f.json()["agent_traces"])

    res_i = client.get("/api/pipeline/inventory")
    assert res_i.status_code == 200
    assert "agent_traces" in res_i.json()
    assert any(t["agent_id"] == "AG-02" for t in res_i.json()["agent_traces"])

    res_w = client.get("/api/pipeline/wastage")
    assert res_w.status_code == 200
    assert "agent_traces" in res_w.json()
    assert any(t["agent_id"] == "AG-03" for t in res_w.json()["agent_traces"])


def test_ai_chat_missing_groq_key_guard(monkeypatch):
    """Verify /ai/chat returns HTTP 400 when GROQ_API_KEY is missing."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from app.core.config import settings
    monkeypatch.setattr(settings, "GROQ_API_KEY", None)

    response = client.post("/api/ai/chat", json={"message": "Hello Copilot"})
    assert response.status_code == 400
    assert "GROQ_API_KEY is missing" in response.json()["error"]
