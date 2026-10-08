import io
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_pipeline_status():
    res = client.get("/api/pipeline/status")
    assert res.status_code == 200
    data = res.json()
    assert "has_run" in data
    assert "stages" in data


def test_pipeline_dashboard():
    res = client.get("/api/pipeline/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "has_data" in data


def test_full_pipeline_flow():
    # Create sample retail dataset CSV
    df = pd.DataFrame({
        "product_id": ["SKU-MILK-01", "SKU-RICE-02", "SKU-APPLE-03"],
        "product_name": ["Organic Fresh Milk", "Basmati Rice 5kg", "Kashmir Apples 1kg"],
        "category": ["Dairy", "Staples", "Produce"],
        "current_stock": [150, 800, 50],
        "demand": [500, 300, 200],
        "unit_cost": ["₹65", "₹420", "₹180"],
        "warehouse": ["Mumbai Central", "Pune North", "Thane East"],
        "expiry_date": ["2026-08-30", "2027-01-15", "2026-08-28"],
    })
    csv_bytes = io.BytesIO()
    df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)

    # 1. Run automatic pipeline endpoint
    files = [("files", ("test_retail.csv", csv_bytes.getvalue(), "text/csv"))]
    res = client.post("/api/data-collection/pipeline", files=files)
    assert res.status_code == 200, res.text
    result = res.json()
    assert result["status"] == "success"
    assert result["dataset_summary"]["total_products"] == 3
    assert result["stages"]["wastage"] == "completed"

    # 2. Check pipeline dashboard endpoint
    dash_res = client.get("/api/pipeline/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["has_data"] is True
    assert len(dash_data["aiRecommendations"]) > 0

    # 3. Check pipeline forecast endpoint
    fc_res = client.get("/api/pipeline/forecast")
    assert fc_res.status_code == 200
    fc_data = fc_res.json()
    assert fc_data["has_data"] is True
    assert fc_data["model"] == "XGBoost"

    # 4. Check pipeline inventory endpoint
    inv_res = client.get("/api/pipeline/inventory")
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["has_data"] is True
    assert len(inv_data["items"]) == 3

    # 5. Check pipeline wastage endpoint
    wst_res = client.get("/api/pipeline/wastage")
    assert wst_res.status_code == 200
    wst_data = wst_res.json()
    assert wst_data["has_data"] is True
    assert len(wst_data["decisions"]) == 3


def test_wastage_agent_expiry_logic():
    """Verify Wastage Agent rules: <=7 days discount, >7 days normal, expired Do Not Sell, missing expiry handled."""
    from datetime import datetime, timezone, timedelta
    today = datetime.now(timezone.utc).date()

    past_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
    near_urgent = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    near_medium = (today + timedelta(days=4)).strftime("%Y-%m-%d")
    near_low = (today + timedelta(days=6)).strftime("%Y-%m-%d")
    future_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")

    df = pd.DataFrame({
        "product_id": ["SKU-EXP", "SKU-URGENT", "SKU-MED", "SKU-LOW", "SKU-NORMAL", "SKU-NOEXP"],
        "product_name": ["Expired Yogurt", "Urgent Milk", "Medium Cheese", "Low Bread", "Fresh Rice", "Salt (No Expiry)"],
        "category": ["Dairy", "Dairy", "Dairy", "Bakery", "Grains", "Staples"],
        "current_stock": [50, 100, 150, 200, 500, 1000],
        "demand": [100, 120, 150, 200, 400, 500],
        "unit_cost": ["₹40", "₹60", "₹150", "₹45", "₹80", "₹20"],
        "warehouse": ["Mumbai Central", "Mumbai Central", "Pune North", "Thane East", "Mumbai Central", "Pune North"],
        "expiry_date": [past_date, near_urgent, near_medium, near_low, future_date, None],
    })
    csv_bytes = io.BytesIO()
    df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)

    files = [("files", ("test_expiry_rules.csv", csv_bytes.getvalue(), "text/csv"))]
    res = client.post("/api/data-collection/pipeline", files=files)
    assert res.status_code == 200, res.text

    wst_res = client.get("/api/pipeline/wastage")
    assert wst_res.status_code == 200
    wst = wst_res.json()
    assert wst["has_data"] is True

    decisions = {d["product_id"]: d for d in wst["decisions"]}

    # 1. Expired product (< 0 days)
    assert decisions["SKU-EXP"]["decision"] == "Do Not Sell"
    assert decisions["SKU-EXP"]["discount"] == "N/A"
    assert decisions["SKU-EXP"]["days_remaining"] < 0

    # 2. Urgent near-expiry (<= 2 days)
    assert decisions["SKU-URGENT"]["decision"] == "Apply Discount"
    assert any(p in decisions["SKU-URGENT"]["discount"] for p in ["30%", "50%"])
    assert 0 <= decisions["SKU-URGENT"]["days_remaining"] <= 4

    # 3. Medium near-expiry (3-4 days)
    assert decisions["SKU-MED"]["decision"] == "Apply Discount"
    assert any(p in decisions["SKU-MED"]["discount"] for p in ["20%", "30%"])
    assert 3 <= decisions["SKU-MED"]["days_remaining"] <= 5

    # 4. Low near-expiry (5-7 days)
    assert decisions["SKU-LOW"]["decision"] == "Apply Discount"
    assert any(p in decisions["SKU-LOW"]["discount"] for p in ["10%", "20%"])
    assert 5 <= decisions["SKU-LOW"]["days_remaining"] <= 7

    # 5. Normal product (> 7 days)
    assert decisions["SKU-NORMAL"]["decision"] == "Sell Normally"
    assert decisions["SKU-NORMAL"]["discount"] == "None"
    assert decisions["SKU-NORMAL"]["days_remaining"] > 7

    # 6. Missing expiry date
    assert decisions["SKU-NOEXP"]["decision"] == "Sell Normally"
    assert decisions["SKU-NOEXP"]["discount"] == "None"
    assert decisions["SKU-NOEXP"]["days_remaining"] is None

    # Check summary counts
    summary = wst["summary"]
    assert summary["expired_count"] == 1
    assert summary["discount_count"] == 3
    assert summary["normal_count"] == 2

