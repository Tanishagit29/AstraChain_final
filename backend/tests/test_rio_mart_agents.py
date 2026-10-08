"""
Inventory Agent (stockout + overstock) and Wastage Agent (near-expiry + discounts) on the
Rio Mart Unified layout.
"""
import io

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.rio_mart_intelligence import (
    ENRICHED_COLUMNS,
    build_inventory_view,
    build_wastage_view,
    discount_pct_for_days,
    enrich_rio_mart_frame,
    is_rio_mart_format,
)
from app.services.rio_mart_service import RioMartService

client = TestClient(app)


def _row(code, stock, safety=2, rop=7, mx=16, cover=100.0, perishable=False, days=np.nan,
         flag="NOT_TRACKED", risk=None, mrp=100.0):
    return {
        "store_id": "ST01", "store_name": "Rio Mart Test", "product_code": code,
        "product_name": f"ITEM {code}", "sub_cat_name": "TEST", "unit_cost": 80.0, "mrp": mrp,
        "avg_daily_demand_units": 1.2, "expected_next_festival_multiplier": 1.0, "lead_time_days": 4,
        "current_stock": stock, "reorder_point_units": rop, "safety_stock_units": safety,
        "max_stock_units": mx, "days_of_cover": cover, "is_perishable": perishable,
        "perishable_tier": "MEDIUM" if perishable else "LOW", "days_to_nearest_expiry": days,
        "wastage_flag": flag, "nearest_batch_id": f"{code}-ST01-1" if perishable else np.nan,
        "nearest_batch_quantity": 20.0 if perishable else np.nan,
        # The source CSV's own label vocabulary (it has no OVERSTOCK)
        "stockout_risk": risk or ("STOCKOUT" if stock <= 0 else "CRITICAL" if stock <= safety else "AT_RISK" if stock <= rop else "HEALTHY"),
    }


@pytest.fixture
def frame():
    rows = [
        _row(1, 0),                                   # STOCKOUT
        _row(2, 1),                                   # CRITICAL
        _row(3, 5),                                   # AT_RISK
        _row(4, 12, cover=200),                       # HEALTHY (below the ceiling)
        _row(5, 16, cover=150),                       # at max + lots of cover -> OVERSTOCK
        _row(6, 16, cover=20),                        # at max but sells fast   -> HEALTHY
        _row(7, 10, perishable=True, days=1, flag="NEAR_EXPIRY"),    # 50%
        _row(8, 10, perishable=True, days=4, flag="NEAR_EXPIRY"),    # 30%
        _row(9, 10, perishable=True, days=6, flag="NEAR_EXPIRY"),    # 20%
        _row(10, 10, perishable=True, days=9, flag="NEAR_EXPIRY"),   # 10%
        _row(11, 10, perishable=True, days=30, flag="OK"),           # plenty of shelf life
        _row(12, 0, perishable=True, days=1, flag="NEAR_EXPIRY"),    # nothing on shelf to discount
    ]
    return pd.DataFrame(rows)


def test_discount_tiers():
    assert [discount_pct_for_days(d) for d in (0, 1, 2, 3, 5, 6, 7, 8, 10, 11)] == [50, 50, 50, 30, 30, 20, 20, 10, 10, 0]
    assert discount_pct_for_days(-3) == 0          # expired items are never discounted
    assert discount_pct_for_days(None) == 0
    assert discount_pct_for_days(float("nan")) == 0


def test_overstock_added_alongside_stockout(frame):
    assert is_rio_mart_format(frame)
    out = enrich_rio_mart_frame(frame).set_index("product_code")
    assert out.loc[1, "stockout_risk"] == "STOCKOUT"
    assert out.loc[2, "stockout_risk"] == "CRITICAL"
    assert out.loc[3, "stockout_risk"] == "AT_RISK"
    assert out.loc[4, "stockout_risk"] == "HEALTHY"
    assert out.loc[5, "stockout_risk"] == "OVERSTOCK"
    assert out.loc[6, "stockout_risk"] == "HEALTHY"
    assert out.loc[1, "inventory_action"] == "REORDER_NOW"
    assert out.loc[5, "inventory_action"] == "REDUCE_NEXT_ORDER"
    assert out.loc[1, "suggested_reorder_qty"] == 16 and out.loc[5, "suggested_reorder_qty"] == 0


def test_enrichment_is_idempotent(frame):
    once = enrich_rio_mart_frame(frame)
    twice = enrich_rio_mart_frame(once)
    for col in ["stockout_risk"] + ENRICHED_COLUMNS:
        assert once[col].fillna(-1).equals(twice[col].fillna(-1)), col


def test_near_expiry_discount_columns(frame):
    out = enrich_rio_mart_frame(frame).set_index("product_code")
    assert [int(out.loc[c, "near_expiry_discount_pct"]) for c in (7, 8, 9, 10)] == [50, 30, 20, 10]
    assert out.loc[7, "near_expiry_discounted_price"] == 50.0      # MRP 100 - 50%
    assert out.loc[11, "near_expiry_discount_pct"] == 0             # not near expiry
    assert out.loc[12, "near_expiry_discount_pct"] == 0             # out of stock
    assert out.loc[1, "near_expiry_discount_pct"] == 0              # non-perishable
    assert np.isnan(out.loc[1, "near_expiry_discounted_price"])


def test_inventory_view_lists_both_stockout_and_overstock(frame):
    items, summary = build_inventory_view(frame)
    statuses = {i["status"] for i in items}
    assert {"Stockout Risk", "Overstock", "Low Stock", "Available"} <= statuses
    assert summary["stockout_count"] == 2 + 1        # STOCKOUT + CRITICAL + the 0-stock perishable
    assert summary["overstock_count"] == 1
    assert summary["total_items"] == len(frame)
    stockout = next(i for i in items if i["risk_label"] == "STOCKOUT")
    assert stockout["recommended_action"] == "REORDER_NOW" and stockout["stock_ratio"] == 0


def test_wastage_view_shows_only_near_expiry_with_discounts(frame):
    decisions, summary = build_wastage_view(frame)
    assert [d["days_remaining"] for d in decisions] == [1, 4, 6, 9]
    assert [d["discount"] for d in decisions] == ["50%", "30%", "20%", "10%"]
    assert all(d["decision"] == "Apply Discount" and d["discounted_price"] < d["mrp"] for d in decisions)
    assert all(d["days_remaining"] >= 0 for d in decisions)
    assert summary["expired_count"] == 0
    assert summary["near_expiry_count"] == summary["discount_count"] == 4


def test_upload_pipeline_no_expired_and_both_stock_statuses(frame):
    """
    Regression: uploading this layout used to read `days_to_nearest_expiry` (e.g. 5) as a DATE
    ("5th of this month"), so every product came out expired and nothing was flagged stockout.
    """
    buf = io.BytesIO()
    frame.to_csv(buf, index=False)
    res = client.post("/api/data-collection/pipeline", files=[("files", ("rio.csv", buf.getvalue(), "text/csv"))])
    assert res.status_code == 200, res.text

    inv = client.get("/api/pipeline/inventory").json()
    assert inv["summary"]["stockout_count"] > 0 and inv["summary"]["overstock_count"] > 0
    assert {"Stockout Risk", "Overstock"} <= {i["status"] for i in inv["items"]}

    wst = client.get("/api/pipeline/wastage").json()
    assert wst["summary"]["expired_count"] == 0
    assert not any(d["decision"] == "Do Not Sell" for d in wst["decisions"])
    assert sorted(d["discount"] for d in wst["decisions"]) == ["10%", "20%", "30%", "50%"]


def test_agent_endpoints():
    inv = client.get("/api/rio-mart/inventory-agent")
    assert inv.status_code == 200
    body = inv.json()
    assert body["summary"]["stockout_count"] > 0 and body["summary"]["overstock_count"] > 0
    assert {"Stockout Risk", "Overstock"} <= {i["status"] for i in body["items"]}

    wst = client.get("/api/rio-mart/wastage-agent")
    assert wst.status_code == 200
    w = wst.json()
    assert w["summary"]["expired_count"] == 0 and len(w["decisions"]) > 0
    assert all(d["days_remaining"] >= 0 and d["discount_pct"] in (10, 20, 30, 50) for d in w["decisions"])

    overstock = client.get("/api/rio-mart/inventory?limit=5&risk=OVERSTOCK").json()
    assert overstock["total"] > 0
    assert all(i["stockout_risk"] == "OVERSTOCK" for i in overstock["items"])


def test_shipped_csv_contains_overstock_and_discounts():
    df = RioMartService._load_data()
    assert {"STOCKOUT", "OVERSTOCK"} <= set(df["stockout_risk"].unique())
    for col in ENRICHED_COLUMNS:
        assert col in df.columns
    discounted = df[df["near_expiry_discount_pct"] > 0]
    assert len(discounted) > 0
    assert discounted["is_perishable"].all() and (discounted["days_to_nearest_expiry"] >= 0).all()
