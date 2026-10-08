def test_get_automation_rules(client):
    response = client.get("/api/automation/rules")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

def test_approve_action(client):
    response = client.post(
        "/api/automation/approve",
        json={"rule_id": "AUT-101", "action": "APPROVE"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
