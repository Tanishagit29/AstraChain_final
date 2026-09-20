def test_get_inventory_paginated_and_filtered(client):
    res = client.get("/api/inventory?page=1&limit=10&category=Dairy")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    payload = data["data"]
    assert "items" in payload
    assert "total" in payload
    assert payload["page"] == 1
    assert payload["limit"] == 10
    for item in payload["items"]:
        assert item["category"] == "Dairy"
        assert "safetyStock" in item
        assert "reorderPoint" in item


def test_inventory_crud_lifecycle(client):
    # Register & Authenticate User
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": "inv_tester@transitops.ai",
            "password": "SecretPassword123!",
            "full_name": "Inventory Tester",
            "role": "OPERATIONS_LEAD"
        }
    )
    assert reg_res.status_code in [200, 201]

    login_res = client.post(
        "/api/auth/login",
        json={"email": "inv_tester@transitops.ai", "password": "SecretPassword123!"}
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create
    new_item = {
        "product_code": "TEST-SKU-999",
        "name": "Test Organic Milk 1L",
        "category": "Dairy",
        "current_stock": 150,
        "forecast_demand": 500,
        "days_remaining": 3,
        "risk": "HIGH",
        "action": "Reorder immediately",
        "warehouse": "Mumbai Central",
        "unit_cost": "₹60"
    }
    create_res = client.post("/api/inventory", json=new_item, headers=headers)
    assert create_res.status_code == 201
    c_data = create_res.json()["data"]
    assert c_data["id"] == "TEST-SKU-999"
    assert c_data["risk"] == "HIGH"

    # 2. Read Detail
    get_res = client.get("/api/inventory/TEST-SKU-999")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["name"] == "Test Organic Milk 1L"

    # 3. Update
    upd_res = client.put("/api/inventory/TEST-SKU-999", json={"current_stock": 800, "risk": "HEALTHY"}, headers=headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["data"]["currentStock"] == 800

    # 4. Delete
    del_res = client.delete("/api/inventory/TEST-SKU-999", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
