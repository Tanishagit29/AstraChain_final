def test_get_suppliers(client):
    response = client.get("/api/suppliers")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

def test_supplier_reliability(client):
    response = client.get("/api/suppliers/reliability")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
