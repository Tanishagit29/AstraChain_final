from datetime import datetime, timedelta, timezone
from typing import Dict

import pandas as pd
from sqlalchemy.orm import Session

from app.models.all_models import Product, Inventory, Wastage, Category
from app.core.logging import logger
from app.services.rio_mart_service import RioMartService
from app.services.rio_mart_intelligence import near_expiry_mask

# How many extra rows per store (on top of the first `max_records_per_store`) are guaranteed for each
# situation the agents care about, so stockout, overstock and near-expiry items are always present.
PRIORITY_ROWS_PER_STORE = 10
NEAR_EXPIRY_PER_TIER_PER_STORE = 3

# The rest of the app (dashboard, AI copilot, reports, Inventory Agent) speaks this risk vocabulary.
# Rio Mart's finer-grained status is kept in the human-readable `action` text.
_RISK_MAP = {
    "STOCKOUT": "HIGH",
    "CRITICAL": "HIGH",
    "AT_RISK": "MEDIUM",
    "HEALTHY": "HEALTHY",
    "OVERSTOCK": "OVERSTOCK",
}


def _inventory_action(row) -> str:
    status = str(row["stockout_risk"]).upper()
    if status == "STOCKOUT":
        return f"STOCKOUT: reorder {int(row['suggested_reorder_qty'])} units now"
    if status == "CRITICAL":
        return f"CRITICAL: urgent reorder of {int(row['suggested_reorder_qty'])} units (reorder point {int(row['reorder_point_units'])})"
    if status == "AT_RISK":
        return f"AT RISK: reorder {int(row['suggested_reorder_qty'])} units soon (reorder point {int(row['reorder_point_units'])})"
    if status == "OVERSTOCK":
        return f"OVERSTOCK: {int(row['current_stock'])} units on hand (~{int(row['days_of_cover'])} days cover) - reduce next order"
    return "Optimal stock"


def _select_sample(df: pd.DataFrame, max_records_per_store: int) -> pd.DataFrame:
    base = df.groupby("store_id", group_keys=False).head(max_records_per_store)

    stockout = df[df["stockout_risk"].isin(["STOCKOUT", "CRITICAL"])]
    overstock = df[df["stockout_risk"] == "OVERSTOCK"]
    near = df[near_expiry_mask(df)].sort_values("days_to_nearest_expiry", kind="mergesort")

    parts = [base]
    for subset in (stockout, overstock):
        parts.append(subset.groupby("store_id", group_keys=False).head(PRIORITY_ROWS_PER_STORE))
    # Near-expiry: a few per store from EACH discount tier (50/30/20/10%), not just the 1-day items
    for lo, hi in ((-1, 2), (2, 5), (5, 7), (7, 10_000)):
        tier = near[(near["days_to_nearest_expiry"] > lo) & (near["days_to_nearest_expiry"] <= hi)]
        parts.append(tier.groupby("store_id", group_keys=False).head(NEAR_EXPIRY_PER_TIER_PER_STORE))
    return pd.concat(parts).drop_duplicates(subset=["store_id", "product_code"])


def seed_rio_mart_data(db: Session, max_records_per_store: int = 200) -> Dict[str, int]:
    """
    Seeds / refreshes products, inventory and wastage records from Rio_Mart_Unified.csv.

    * Inventory carries stockout (HIGH) and OVERSTOCK risk labels.
    * Products carry an expiry date (today + days to nearest expiry) for near-expiry perishables,
      which is what lets the Wastage Agent raise discount alerts.
    * Wastage records exist only for NEAR-EXPIRY items and state the discount to apply.
    Re-running is safe: existing rows are updated in place, not duplicated.
    """
    logger.info("Starting database seeding from Rio_Mart_Unified.csv...")
    df = RioMartService._load_data()
    sample_df = _select_sample(df, max_records_per_store)

    counts = {"seeded_categories": 0, "seeded_products": 0, "seeded_inventory": 0, "seeded_wastage": 0,
              "updated_products": 0, "updated_inventory": 0, "updated_wastage": 0}
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    # 1. Categories
    existing_categories = {c.name for c in db.query(Category.name).all()}
    for cat_name in sample_df["sub_cat_name"].unique():
        if cat_name and str(cat_name) != "nan" and cat_name not in existing_categories:
            db.add(Category(name=str(cat_name), description=f"Rio Mart category: {cat_name}"))
            existing_categories.add(str(cat_name))
            counts["seeded_categories"] += 1
    db.commit()

    category_map = {c.name: c.id for c in db.query(Category).all()}
    products = {p.sku: p for p in db.query(Product).filter(Product.sku.like("RIO-%")).all()}
    inventory = {i.product_code: i for i in db.query(Inventory).filter(Inventory.product_code.like("RIO-%")).all()}
    wastage = {w.item_code: w for w in db.query(Wastage).filter(Wastage.item_code.like("WS-RIO-%")).all()}

    # 2. Products, inventory, wastage
    for _, row in sample_df.iterrows():
        p_code = f"RIO-{row['store_id']}-{row['product_code']}"
        p_name = str(row["product_name"])
        sub_cat = str(row["sub_cat_name"])
        unit_cost_str = f"₹{row['unit_cost']:.2f}"
        status = str(row["stockout_risk"]).upper()
        risk = _RISK_MAP.get(status, "HEALTHY")
        days_cover = int(row["days_of_cover"]) if row["days_of_cover"] > 0 else 10
        is_near = int(row["near_expiry_discount_pct"]) > 0
        expiry_dt = today + timedelta(days=int(row["days_to_nearest_expiry"])) if is_near else None

        # Product
        prod = products.get(p_code)
        if prod is None:
            prod = Product(
                sku=p_code, name=p_name, category_name=sub_cat, category_id=category_map.get(sub_cat),
                unit_cost=unit_cost_str, days_remaining=days_cover, risk_level=risk, expiry_date=expiry_dt,
            )
            db.add(prod)
            db.flush()
            products[p_code] = prod
            counts["seeded_products"] += 1
        else:
            prod.risk_level = risk
            prod.days_remaining = days_cover
            prod.expiry_date = expiry_dt
            counts["updated_products"] += 1

        # Inventory
        progress = min(100, max(5, int((row["current_stock"] / max(1, row["max_stock_units"])) * 100)))
        inv = inventory.get(p_code)
        if inv is None:
            db.add(Inventory(
                product_code=p_code, name=p_name, category=sub_cat,
                current_stock=int(row["current_stock"]),
                forecast_demand=int(row["avg_daily_demand_units"] * 30),
                days_remaining=days_cover, progress=progress, risk=risk,
                action=_inventory_action(row), warehouse=str(row["store_name"]),
                unit_cost=unit_cost_str, product_id=prod.id,
            ))
            counts["seeded_inventory"] += 1
        else:
            inv.current_stock = int(row["current_stock"])
            inv.days_remaining = days_cover
            inv.progress = progress
            inv.risk = risk
            inv.action = _inventory_action(row)
            inv.product_id = prod.id
            counts["updated_inventory"] += 1

        # Wastage: near-expiry items only, each with the discount to apply
        if is_near:
            w_code = f"WS-{p_code}"
            days = int(row["days_to_nearest_expiry"])
            pct = int(row["near_expiry_discount_pct"])
            batch_qty = int(row["nearest_batch_quantity"]) if row["nearest_batch_quantity"] > 0 else int(row["current_stock"])
            units = min(int(row["current_stock"]), batch_qty)
            fields = dict(
                product=p_name,
                batch=str(row["nearest_batch_id"]) if row["nearest_batch_id"] else f"BATCH-{row['product_code']}",
                quantity=f"{units} units",
                reason=f"Near expiry: {days} day(s) left (Perishable Tier: {row['perishable_tier']})",
                loss_amount=f"₹{units * row['unit_cost']:.2f}",
                severity="HIGH" if days <= 2 else "MEDIUM",
                agent_intervention=(
                    f"Apply {pct}% markdown: MRP ₹{row['mrp']:.2f} -> ₹{row['near_expiry_discounted_price']:.2f}"
                ),
            )
            w = wastage.get(w_code)
            if w is None:
                w = Wastage(item_code=w_code, **fields)
                db.add(w)
                wastage[w_code] = w
                counts["seeded_wastage"] += 1
            else:
                for k, v in fields.items():
                    setattr(w, k, v)
                counts["updated_wastage"] += 1

    db.commit()
    logger.info(f"Rio Mart Seeding Completed: {counts}")
    return counts
