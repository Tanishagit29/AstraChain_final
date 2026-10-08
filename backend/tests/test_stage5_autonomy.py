import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models import all_models
from app.main import app
from app.database.session import get_db
from app.services.autonomous_scheduler import autonomous_scheduler
from app.services.pipeline_state import pipeline_state

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_stage5.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db_stage5():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db_stage5
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os
    if os.path.exists("./test_stage5.db"):
        try:
            os.remove("./test_stage5.db")
        except Exception:
            pass


def test_autonomous_scheduler_manual_sweep():
    """Verify manual run_autonomous_sweep executes without errors."""
    db = TestingSessionLocal()
    try:
        result = autonomous_scheduler.run_autonomous_sweep(db)
        assert result["status"] == "SUCCESS"
        assert result["sweeps_completed"] >= 1
        assert "actions_triggered" in result
        
        # Verify trace added to pipeline_state
        assert any(t["agent_id"] == "AG-SCHEDULER" for t in pipeline_state.agent_traces)
    finally:
        db.close()


def test_trigger_sweep_endpoint():
    """Verify /api/automation/trigger-sweep endpoint."""
    res = client.post("/api/automation/trigger-sweep")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "SUCCESS"


def test_scheduler_status_endpoint():
    """Verify /api/automation/scheduler-status endpoint."""
    res = client.get("/api/automation/scheduler-status")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "is_running" in body["data"]
    assert "sweeps_completed" in body["data"]
