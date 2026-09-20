def test_run_multi_agent_pipeline(client, auth_headers):
    response = client.post("/api/multi-agent/run?product_id=MK-001-F&horizon_days=30", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "pipeline" in data
    assert len(data["pipeline"]) == 3
    assert "key_actions" in data


def test_get_multi_agent_insights(client, auth_headers):
    response = client.get("/api/multi-agent/insights", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "demand_agent" in data
    assert "inventory_agent" in data
    assert "wastage_agent" in data
    assert data["demand_agent"]["model"] == "XGBoost Regressor v2.4"


def test_execute_key_action(client, auth_headers):
    payload = {
        "action_type": "MANAGER_APPROVAL",
        "target_id": "ACT-TEST-001"
    }
    response = client.post("/api/multi-agent/action/execute", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["action_type"] == "MANAGER_APPROVAL"
