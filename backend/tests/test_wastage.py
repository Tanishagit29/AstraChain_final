def test_get_wastage(client):
    response = client.get("/api/wastage")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

def test_discount_recommendations(client):
    response = client.get("/api/wastage/discount-recommendations")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

def test_add_near_expiry_item_endpoint(client):
    payload = {
        "product_name": "Organic Almond Milk 1L",
        "category": "Dairy & Refrigerated",
        "days_remaining": 2,
        "unit_cost": "₹140",
        "current_stock": 80
    }
    response = client.post("/api/pipeline/wastage/add", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["data"]["product_name"] == "Organic Almond Milk 1L"
    assert res_data["data"]["decision"] == "Apply Discount"
    assert "50%" in res_data["data"]["discount"]

    # Verify pipeline wastage now returns the added item
    wastage_res = client.get("/api/pipeline/wastage")
    assert wastage_res.status_code == 200
    w_json = wastage_res.json()
    assert w_json["has_data"] is True
    assert len(w_json["decisions"]) >= 1
    assert w_json["decisions"][0]["product_name"] == "Organic Almond Milk 1L"

