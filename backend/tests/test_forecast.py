def test_get_forecasts(client):
    response = client.get("/api/forecast")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_generate_forecast(client):
    response = client.post("/api/forecast/generate", json={"horizon_days": 14})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
