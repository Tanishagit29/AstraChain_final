import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models import all_models
from app.main import app
from app.database.session import get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_stage4.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db_stage4():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db_stage4
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os
    if os.path.exists("./test_stage4.db"):
        try:
            os.remove("./test_stage4.db")
        except Exception:
            pass


def test_low_risk_action_auto_executes():
    """Verify reorders <= 500 units auto-execute without requiring manager approval."""
    payload = {
        "action_type": "REORDER",
        "target_id": "SKU-MILK-100",
        "quantity": 300,
        "details": "Routine stock reorder"
    }
    res = client.post("/api/multi-agent/action/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "EXECUTED"
    assert data["requires_approval"] is False


def test_high_impact_action_requires_approval():
    """Verify reorders > 500 units require manager approval and log PENDING_APPROVAL status."""
    payload = {
        "action_type": "REORDER",
        "target_id": "SKU-RICE-999",
        "quantity": 1200,
        "details": "Bulk emergency stock reorder"
    }
    res = client.post("/api/multi-agent/action/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PENDING_APPROVAL"
    assert data["requires_approval"] is True

    # Check pending approvals list
    res_p = client.get("/api/multi-agent/pending-approvals")
    assert res_p.status_code == 200
    pending_data = res_p.json()
    assert pending_data["pending_count"] >= 1
    assert any(a["rule_code"] == "AUT-SKU-RICE-999" for a in pending_data["pending_actions"])


def test_approve_high_impact_action():
    """Verify executing a pending approval task updates status to EXECUTED."""
    # 1. Trigger high-impact discount proposal
    eval_res = client.post("/api/multi-agent/action/evaluate", json={
        "action_type": "DISCOUNT",
        "target_id": "SKU-EXP-555",
        "discount_pct": 50.0,
        "details": "Emergency 50% discount for 1-day expiry"
    })
    assert eval_res.json()["status"] == "PENDING_APPROVAL"

    # 2. Manager approves the action via /action/execute
    exec_res = client.post("/api/multi-agent/action/execute", json={
        "action_type": "MANAGER_APPROVAL",
        "target_id": "SKU-EXP-555"
    })
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "EXECUTED"

    # 3. Verify it is no longer pending
    pending_res = client.get("/api/multi-agent/pending-approvals")
    assert not any(a["rule_code"] == "AUT-SKU-EXP-555" for a in pending_res.json()["pending_actions"])
