import io
import pandas as pd
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes.data_collection import robust_parse_date

client = TestClient(app)


def test_robust_parse_date_direct():
    """Verify robust_parse_date handles DD/MM/YYYY, ISO, textual, and Excel dates accurately without day-month inversion."""
    assert robust_parse_date("01/10/2026") == datetime(2026, 10, 1)
    assert robust_parse_date("15/10/2026") == datetime(2026, 10, 15)
    assert robust_parse_date("01-10-2026") == datetime(2026, 10, 1)
    assert robust_parse_date("10/01/2026") == datetime(2026, 1, 10)
    assert robust_parse_date("01/09/2026") == datetime(2026, 9, 1)
    assert robust_parse_date("1 October 2026") == datetime(2026, 10, 1)
    assert robust_parse_date("October 1, 2026") == datetime(2026, 10, 1)
    assert robust_parse_date("2026-10-01") == datetime(2026, 10, 1)
    assert robust_parse_date("2026/10/01") == datetime(2026, 10, 1)
    assert robust_parse_date("01.10.2026") == datetime(2026, 10, 1)


def test_user_requested_dates_in_pipeline():
    """
    Test user exact test cases:
    - 01/10/2026 -> 2026-10-01 (32 days remaining from 2026-08-30 -> Sell Normally)
    - 01/09/2026 -> 2026-09-01 (2 days remaining from 2026-08-30 -> Apply Discount 30%)
    - 10/01/2026 -> 2026-01-10 (expired 232 days ago -> Do Not Sell)
    """
    df = pd.DataFrame({
        "product_id": ["SKU-OCT-01", "SKU-SEP-01", "SKU-JAN-10", "SKU-OCT-15"],
        "product_name": ["October Milk", "September Cheese", "January Bread (Expired)", "Mid October Paneer"],
        "category": ["Dairy", "Dairy", "Bakery", "Dairy"],
        "current_stock": [100, 150, 80, 200],
        "demand": [200, 180, 100, 250],
        "unit_cost": ["₹70", "₹140", "₹40", "₹160"],
        "warehouse": ["Mumbai Central", "Pune North", "Thane East", "Mumbai Central"],
        "expiry_date": ["01/10/2026", "01/09/2026", "10/01/2026", "15/10/2026"],
    })
    csv_bytes = io.BytesIO()
    df.to_csv(csv_bytes, index=False)
    csv_bytes.seek(0)

    files = [("files", ("test_user_dates.csv", csv_bytes.getvalue(), "text/csv"))]
    res = client.post("/api/data-collection/pipeline", files=files)
    assert res.status_code == 200, res.text

    wst_res = client.get("/api/pipeline/wastage")
    assert wst_res.status_code == 200
    wst = wst_res.json()
    assert wst["has_data"] is True

    decisions = {d["product_id"]: d for d in wst["decisions"]}

    # 1. 01/10/2026 -> 2026-10-01
    oct_item = decisions["SKU-OCT-01"]
    assert oct_item["expiry_date"] == "2026-10-01"
    expected_oct_days = (datetime.strptime("2026-10-01", "%Y-%m-%d").date() - datetime.now(timezone.utc).date()).days
    assert oct_item["days_remaining"] == expected_oct_days

    # 2. 01/09/2026 -> 2026-09-01
    sep_item = decisions["SKU-SEP-01"]
    assert sep_item["expiry_date"] == "2026-09-01"
    expected_sep_days = (datetime.strptime("2026-09-01", "%Y-%m-%d").date() - datetime.now(timezone.utc).date()).days
    assert sep_item["days_remaining"] == expected_sep_days
    if expected_sep_days < 0:
        assert sep_item["decision"] == "Do Not Sell"
    else:
        assert sep_item["decision"] == "Apply Discount"

    # 3. 10/01/2026 -> 2026-01-10
    jan_item = decisions["SKU-JAN-10"]
    assert jan_item["expiry_date"] == "2026-01-10"
    expected_jan_days = (datetime.strptime("2026-01-10", "%Y-%m-%d").date() - datetime.now(timezone.utc).date()).days
    assert jan_item["days_remaining"] == expected_jan_days
    assert jan_item["decision"] == "Do Not Sell"
    assert jan_item["discount"] == "N/A"

    # 4. 15/10/2026 -> 2026-10-15
    oct15_item = decisions["SKU-OCT-15"]
    assert oct15_item["expiry_date"] == "2026-10-15"
    expected_oct15_days = (datetime.strptime("2026-10-15", "%Y-%m-%d").date() - datetime.now(timezone.utc).date()).days
    assert oct15_item["days_remaining"] == expected_oct15_days
    assert oct15_item["decision"] == "Sell Normally"
    assert oct15_item["discount"] == "None"
