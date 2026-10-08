def test_get_known_locations(client):
    response = client.get("/api/routes/locations")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Mumbai Central Port" in data["data"]
    assert "Pune Logistics Hub" in data["data"]


def test_optimize_multi_stop_route(client):
    response = client.post(
        "/api/routes/optimize-multi-stop",
        json={
            "truck_id": "MH-04-JK-4821",
            "origin": "Mumbai Central Port",
            "stops": [
                "Pune Logistics Hub",
                "Nashik Warehouse",
                "Thane Cold Storage",
                "Solapur Distribution",
            ],
            "return_to_origin": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]

    assert data["truck_id"] == "MH-04-JK-4821"
    assert data["origin"] == "Mumbai Central Port"
    assert data["total_stops"] == 4
    # Optimized tour must start and end at the origin (return_to_origin=True)
    assert data["optimized_sequence"][0] == "Mumbai Central Port"
    assert data["optimized_sequence"][-1] == "Mumbai Central Port"
    # Every requested stop must appear exactly once in the optimized tour
    assert set(data["optimized_sequence"][1:-1]) == {
        "Pune Logistics Hub", "Nashik Warehouse", "Thane Cold Storage", "Solapur Distribution"
    }
    # The 2-opt optimized distance should never be worse than the naive input order
    assert data["total_distance_km"] <= data["naive_distance_km"] + 1e-6
    assert data["distance_saved_km"] >= 0
    assert data["fuel_saved_inr"] >= 0
    assert len(data["legs"]) == 5
    assert data["algorithm"] == "Nearest Neighbor + 2-Opt"


def test_optimize_multi_stop_route_rejects_unknown_location(client):
    response = client.post(
        "/api/routes/optimize-multi-stop",
        json={
            "truck_id": "MH-04-JK-4821",
            "origin": "Mumbai Central Port",
            "stops": ["Atlantis Warehouse", "Pune Logistics Hub"],
        },
    )
    assert response.status_code == 400


def test_optimize_multi_stop_route_requires_at_least_two_stops(client):
    response = client.post(
        "/api/routes/optimize-multi-stop",
        json={
            "truck_id": "MH-04-JK-4821",
            "origin": "Mumbai Central Port",
            "stops": ["Pune Logistics Hub"],
        },
    )
    assert response.status_code == 400
