import pytest
from app.services.pipeline_state import pipeline_state


def test_get_notifications(client):
    # Prime pipeline state items
    pipeline_state.load_default_near_expiry_items()

    res = client.get("/api/notifications")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "data" in data
    assert "unread_count" in data
    assert "stockout_count" in data
    assert len(data["data"]) > 0

    # Verify stockout notification structure
    stockouts = [n for n in data["data"] if n.get("type") == "STOCKOUT"]
    assert len(stockouts) > 0
    first_stockout = stockouts[0]
    assert "product_id" in first_stockout
    assert "product_name" in first_stockout
    assert first_stockout["can_restock"] is True


def test_single_click_restock_notification(client):
    pipeline_state.load_default_near_expiry_items()

    # Get a stockout item
    res = client.get("/api/notifications")
    stockouts = [n for n in res.json()["data"] if n.get("type") == "STOCKOUT" and n.get("can_restock")]
    assert len(stockouts) > 0
    target = stockouts[0]
    target_pid = target["product_id"]

    # Execute 1-Click Restock
    restock_res = client.post(
        "/api/notifications/restock",
        json={
            "product_id": target_pid,
            "quantity": 500,
            "notification_id": target["id"]
        }
    )
    assert restock_res.status_code == 200
    result = restock_res.json()
    assert result["success"] is True
    assert "restocked" in result["message"].lower()
    assert result["quantity_added"] == 500

    # Verify the notification is now marked as restocked
    updated_res = client.get("/api/notifications")
    matched = [n for n in updated_res.json()["data"] if n.get("product_id") == target_pid]
    if matched:
        assert matched[0]["is_restocked"] is True
        assert matched[0]["can_restock"] is False


def test_mark_all_notifications_read(client):
    res = client.post("/api/notifications/mark-all-read")
    assert res.status_code == 200
    assert res.json()["success"] is True

    unread_res = client.get("/api/notifications?unread_only=true")
    assert unread_res.status_code == 200
    assert unread_res.json()["unread_count"] == 0


def test_inventory_restock_endpoint(client):
    res = client.post(
        "/api/inventory/restock",
        json={
            "product_id": "MK-001-F",
            "quantity": 300
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["quantity"] == 300
