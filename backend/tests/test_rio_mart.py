import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.rio_mart_service import RioMartService

client = TestClient(app)

def test_rio_mart_service_load():
    summary = RioMartService.get_summary()
    assert summary["dataset"] == "Rio Mart Unified Dataset"
    assert summary["total_records"] > 200000
    assert summary["total_stores"] > 0
    assert "stockout_risk_breakdown" in summary

def test_rio_mart_stores():
    stores = RioMartService.get_stores()
    assert isinstance(stores, list)
    assert len(stores) > 0
    first_store = stores[0]
    assert "store_id" in first_store
    assert "store_name" in first_store
    assert "latitude" in first_store
    assert "longitude" in first_store

def test_rio_mart_inventory_pagination_and_filter():
    res = RioMartService.get_inventory(page=1, limit=10, store_id="ST01")
    assert res["total"] > 0
    assert len(res["items"]) <= 10
    for item in res["items"]:
        assert item["store_id"].lower() == "st01"

def test_rio_mart_festivals():
    festivals = RioMartService.get_festivals_impact()
    assert isinstance(festivals, list)
    assert len(festivals) > 0
    for f in festivals:
        assert "festival_name" in f
        assert "avg_demand_multiplier" in f

def test_rio_mart_api_summary_endpoint():
    response = client.get("/api/rio-mart/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] > 200000
    assert "total_inventory_valuation_inr" in data

def test_rio_mart_api_stores_endpoint():
    response = client.get("/api/rio-mart/stores")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

def test_rio_mart_api_inventory_endpoint():
    response = client.get("/api/rio-mart/inventory?limit=5&risk=CRITICAL")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) <= 5
    for item in data["items"]:
        assert item["stockout_risk"].upper() == "CRITICAL"

