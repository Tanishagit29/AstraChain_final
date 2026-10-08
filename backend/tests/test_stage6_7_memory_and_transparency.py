import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models import all_models
from app.main import app
from app.database.session import get_db
from app.services.pipeline_state import pipeline_state

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_stage6_7.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db_stage67():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db_stage67
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os
    if os.path.exists("./test_stage6_7.db"):
        try:
            os.remove("./test_stage6_7.db")
        except Exception:
            pass


def test_agent_message_board():
    """Verify posting and retrieving inter-agent messages."""
    post_res = client.post("/api/multi-agent/messages", json={
        "sender_agent_id": "AG-01",
        "sender_agent_name": "Demand & Forecasting Agent",
        "target_agent_id": "AG-02",
        "subject": "Diwali Demand Spike Alert",
        "content": "Expect 45% demand increase for Dairy products during Diwali window.",
        "importance": "HIGH"
    })
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "success"

    get_res = client.get("/api/multi-agent/messages")
    assert get_res.status_code == 200
    msg_data = get_res.json()
    assert msg_data["count"] >= 1
    assert any(m["subject"] == "Diwali Demand Spike Alert" for m in msg_data["messages"])


def test_decision_memory():
    """Verify storing and retrieving persistent decision memory entries."""
    post_res = client.post("/api/multi-agent/decisions", json={
        "agent_id": "AG-03",
        "context_key": "SKU-MILK-101",
        "decision": "Applied 30% Promo Discount",
        "rationale": "Product expires in 2 days; 30% discount increases inventory velocity.",
        "user_feedback": "APPROVED"
    })
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "success"

    get_res = client.get("/api/multi-agent/decisions?agent_id=AG-03")
    assert get_res.status_code == 200
    dec_data = get_res.json()
    assert dec_data["count"] >= 1
    assert dec_data["decisions"][0]["decision"] == "Applied 30% Promo Discount"


def test_activity_transparency_traces():
    """Verify system-wide activity transparency and execution traces."""
    pipeline_state.start_pipeline()
    pipeline_state.add_agent_trace(
        agent_id="AG-ORCH",
        agent_name="Supply Chain Master Orchestrator Agent",
        task="Coordinate multi-agent supply chain run",
        reasoning_steps=["Step 1: Evaluated forecast", "Step 2: Calculated safety stock"],
        tools_executed=[{"tool": "run_forecast_agent"}, {"tool": "run_inventory_agent"}]
    )

    res = client.get("/api/pipeline/status")
    assert res.status_code == 200
    data = res.json()
    assert "agent_traces" in data
    assert len(data["agent_traces"]) > 0
    assert any(t["agent_id"] == "AG-ORCH" for t in data["agent_traces"])
