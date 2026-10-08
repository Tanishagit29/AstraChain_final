def test_get_routes(client):
    response = client.get("/api/routes")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

def test_optimize_route(client):
    response = client.post(
        "/api/routes/optimize",
        json={
            "truck_id": "MH-04-JK-4821",
            "destination": "Pune Logistics Hub",
            "avoid_traffic": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
