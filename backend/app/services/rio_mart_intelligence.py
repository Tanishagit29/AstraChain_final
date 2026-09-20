"""
Rio Mart Intelligence
=====================
Single source of truth for the two rule-sets that power the Inventory Agent and
the Wastage Agent when they work on the Rio Mart Unified dataset:

1. STOCK STATUS  - every store/SKU row is classified as one of
       STOCKOUT   stock is zero
       CRITICAL   stock <= safety stock
       AT_RISK    stock <= reorder point
       HEALTHY    stock above the reorder point
       OVERSTOCK  stock is sitting at its max-stock ceiling AND holds
                  >= OVERSTOCK_MIN_COVER_DAYS days of cover
   The first four are exactly how the dataset already defines `stockout_risk`.
   The dataset caps stock at `max_stock_units`, so it can never exceed it and
   therefore never contained an overstock label - OVERSTOCK is the new one.

2. NEAR-EXPIRY DISCOUNTS - perishable rows flagged NEAR_EXPIRY get a markdown
   that grows as expiry gets closer (see DISCOUNT_TIERS). Rows that are not
   near expiry get no discount. Nothing here ever surfaces an expired product.

The functions are pure pandas, so they are shared by the CSV loader, the upload
pipeline, the DB seeding script, the agents and the CSV enrichment script.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Tunable business rules
# --------------------------------------------------------------------------- #
OVERSTOCK_MIN_COVER_DAYS = 90          # days of (observed) sales the shelf already holds
NEAR_EXPIRY_MAX_DAYS = 10              # matches the largest value the dataset flags NEAR_EXPIRY

# (max days to expiry, discount %) - first matching tier wins.
DISCOUNT_TIERS: Tuple[Tuple[int, int], ...] = ((2, 50), (5, 30), (7, 20), (10, 10))
MIN_NEAR_EXPIRY_DISCOUNT = DISCOUNT_TIERS[-1][1]

STOCKOUT_LABELS = ("STOCKOUT", "CRITICAL")
VALID_STATUSES = ("STOCKOUT", "CRITICAL", "AT_RISK", "HEALTHY", "OVERSTOCK")

INVENTORY_ACTIONS = {
    "STOCKOUT": "REORDER_NOW",
    "CRITICAL": "URGENT_REORDER",
    "AT_RISK": "REORDER_SOON",
    "OVERSTOCK": "REDUCE_NEXT_ORDER",
    "HEALTHY": "OPTIMAL",
}

# Columns this module adds to the CSV (stockout_risk is updated in place).
ENRICHED_COLUMNS = [
    "inventory_action",
    "suggested_reorder_qty",
    "near_expiry_discount_pct",
    "near_expiry_discounted_price",
]

REQUIRED_INVENTORY_COLUMNS = {
    "store_id", "product_code", "current_stock",
    "reorder_point_units", "safety_stock_units", "max_stock_units",
}


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def discount_pct_for_days(days: Any) -> int:
    """Discount % for a given number of days left to expiry (0 = no discount)."""
    try:
        if days is None or pd.isna(days):
            return 0
        d = float(days)
    except (TypeError, ValueError):
        return 0
    if d < 0:
        return 0  # already expired - never discounted, never surfaced as near-expiry
    for max_days, pct in DISCOUNT_TIERS:
        if d <= max_days:
            return pct
    return 0


def _num(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce")
    return pd.Series(np.nan if default is None else default, index=df.index, dtype="float64")


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "y"])


def is_rio_mart_format(df: Optional[pd.DataFrame]) -> bool:
    """True when the frame carries the Rio Mart per-store inventory policy columns."""
    if df is None or df.empty:
        return False
    return REQUIRED_INVENTORY_COLUMNS.issubset(set(df.columns))


def _perishable_mask(df: pd.DataFrame) -> pd.Series:
    if "is_perishable" in df.columns:
        return _as_bool(df["is_perishable"])
    return _num(df, "days_to_nearest_expiry", default=None).notna()


# --------------------------------------------------------------------------- #
# Enrichment (idempotent - safe to run on an already-enriched frame)
# --------------------------------------------------------------------------- #
def enrich_rio_mart_frame(df: pd.DataFrame, copy: bool = True) -> pd.DataFrame:
    """
    Returns `df` (a copy unless copy=False) where
      * `stockout_risk` also carries OVERSTOCK, and
      * ENRICHED_COLUMNS (inventory action, reorder qty, near-expiry discount) exist.
    Existing values in every other column are left untouched.
    """
    out = df.copy() if copy else df

    stock = _num(out, "current_stock").fillna(0)
    safety = _num(out, "safety_stock_units").fillna(0)
    reorder = _num(out, "reorder_point_units").fillna(0)
    max_stock = _num(out, "max_stock_units").fillna(0)

    # --- stock status -------------------------------------------------------
    computed = np.select(
        [stock <= 0, stock <= safety, stock <= reorder],
        ["STOCKOUT", "CRITICAL", "AT_RISK"],
        default="HEALTHY",
    )
    if "stockout_risk" in out.columns:
        given = out["stockout_risk"].astype(str).str.strip().str.upper()
        status = pd.Series(np.where(given.isin(VALID_STATUSES), given, computed), index=out.index)
    else:
        status = pd.Series(computed, index=out.index)

    if "days_of_cover" in out.columns:
        cover = _num(out, "days_of_cover")
    else:
        recent = _num(out, "recent_avg_daily_units_per_store", default=None)
        cover = stock / recent.replace(0, np.nan)
    overstock = (status == "HEALTHY") & (max_stock > 0) & (stock >= max_stock) & (cover >= OVERSTOCK_MIN_COVER_DAYS)
    status = status.where(~overstock, "OVERSTOCK")
    out["stockout_risk"] = status

    out["inventory_action"] = status.map(INVENTORY_ACTIONS)
    needs_stock = status.isin(["STOCKOUT", "CRITICAL", "AT_RISK"])
    out["suggested_reorder_qty"] = np.where(needs_stock, (max_stock - stock).clip(lower=0), 0).astype(int)

    # --- near-expiry discount ----------------------------------------------
    near = near_expiry_mask(out)
    days = _num(out, "days_to_nearest_expiry", default=None)
    tier_pct = np.select(
        [days <= t for t, _ in DISCOUNT_TIERS],
        [p for _, p in DISCOUNT_TIERS],
        default=MIN_NEAR_EXPIRY_DISCOUNT,   # flagged near-expiry but > 10 days: smallest markdown
    )
    pct = pd.Series(np.where(near, tier_pct, 0), index=out.index).astype(int)
    out["near_expiry_discount_pct"] = pct
    mrp = _num(out, "mrp", default=None)
    out["near_expiry_discounted_price"] = np.where(pct > 0, (mrp * (1 - pct / 100.0)).round(2), np.nan)
    return out


def near_expiry_mask(df: pd.DataFrame) -> pd.Series:
    """
    Perishable rows that are near expiry, still have stock to sell and have NOT expired.
    Uses the dataset's own `wastage_flag == NEAR_EXPIRY` when present, otherwise
    falls back to 0 <= days_to_nearest_expiry <= NEAR_EXPIRY_MAX_DAYS.
    """
    days = _num(df, "days_to_nearest_expiry", default=None)
    stock = _num(df, "current_stock").fillna(0)
    perishable = _perishable_mask(df)
    if "wastage_flag" in df.columns:
        flagged = df["wastage_flag"].astype(str).str.strip().str.upper().eq("NEAR_EXPIRY")
    else:
        flagged = days <= NEAR_EXPIRY_MAX_DAYS
    return perishable & flagged & days.notna() & (days >= 0) & (stock > 0)


# --------------------------------------------------------------------------- #
# Record builders
# --------------------------------------------------------------------------- #
def _clean(v: Any) -> Any:
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, float) and np.isnan(v):
        return None
    return v


def _product_id(row: pd.Series) -> str:
    return f"RIO-{row['store_id']}-{int(row['product_code'])}"


def _today() -> "datetime.date":
    return datetime.now(timezone.utc).date()


# --------------------------------------------------------------------------- #
# Inventory Agent view: stockout + overstock side by side
# --------------------------------------------------------------------------- #
_STATUS_LABEL = {
    "STOCKOUT": "Stockout Risk",
    "CRITICAL": "Stockout Risk",
    "AT_RISK": "Low Stock",
    "OVERSTOCK": "Overstock",
    "HEALTHY": "Available",
}


def _inventory_records(rows: pd.DataFrame) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for _, r in rows.iterrows():
        stock = int(r["current_stock"])
        daily = float(r["avg_daily_demand_units"]) if "avg_daily_demand_units" in r and pd.notna(r["avg_daily_demand_units"]) else 0.0
        mult = float(r["expected_next_festival_multiplier"]) if "expected_next_festival_multiplier" in r and pd.notna(r["expected_next_festival_multiplier"]) else 1.0
        lead = float(r["lead_time_days"]) if "lead_time_days" in r and pd.notna(r["lead_time_days"]) else 1.0
        # Demand the shelf must cover while a replenishment order is in transit (festival adjusted)
        predicted = max(1, int(np.ceil(daily * mult * lead)))
        label = str(r["stockout_risk"])
        cost = float(r["unit_cost"]) if "unit_cost" in r and pd.notna(r["unit_cost"]) else 0.0
        records.append({
            "product_id": _product_id(r),
            "product_name": str(r.get("product_name", "")),
            "category": _clean(r.get("sub_cat_name")),
            "current_stock": stock,
            "predicted_demand": predicted,
            "status": _STATUS_LABEL[label],
            "risk_label": label,
            "stock_ratio": round(stock / predicted, 2),
            "warehouse": str(r.get("store_name", r["store_id"])),
            "store_id": str(r["store_id"]),
            "unit_cost": f"₹{cost:.2f}",
            "reorder_point": int(r["reorder_point_units"]),
            "safety_stock": int(r["safety_stock_units"]),
            "max_stock": int(r["max_stock_units"]),
            "days_of_cover": _clean(r.get("days_of_cover")),
            "recommended_action": str(r["inventory_action"]),
            "suggested_reorder_qty": int(r["suggested_reorder_qty"]),
        })
    return records


def _interleave(a: List[Any], b: List[Any]) -> List[Any]:
    merged: List[Any] = []
    for i in range(max(len(a), len(b))):
        if i < len(a):
            merged.append(a[i])
        if i < len(b):
            merged.append(b[i])
    return merged


def _prepare(df: pd.DataFrame, already_enriched: bool) -> pd.DataFrame:
    frame = df if already_enriched else enrich_rio_mart_frame(df)
    if not frame.index.is_unique:
        frame = frame.reset_index(drop=True)
    return frame


def build_inventory_view(
    df: pd.DataFrame,
    stockout_n: int = 30,
    overstock_n: int = 30,
    low_stock_n: int = 20,
    available_n: int = 15,
    already_enriched: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Builds the Inventory Agent output: a prioritised item list containing BOTH stockout
    and overstock items (interleaved so the top of the list shows both), plus
    dataset-wide summary counts.
    """
    frame = _prepare(df, already_enriched)
    total = len(frame)
    status = frame["stockout_risk"]
    counts = status.value_counts().to_dict()
    n_stockout = int(counts.get("STOCKOUT", 0))
    n_critical = int(counts.get("CRITICAL", 0))
    n_low = int(counts.get("AT_RISK", 0))
    n_over = int(counts.get("OVERSTOCK", 0))
    n_ok = int(counts.get("HEALTHY", 0))

    velocity = _num(frame, "avg_daily_demand_units").fillna(0) * _num(frame, "mrp").fillna(0)
    capital = _num(frame, "current_stock").fillna(0) * _num(frame, "unit_cost").fillna(0)

    def top(labels: Tuple[str, ...], score: pd.Series, n: int) -> pd.DataFrame:
        idx = frame.index[status.isin(labels)]
        best = score.loc[idx].sort_values(ascending=False, kind="mergesort").head(n)
        return frame.loc[best.index]

    # Stockouts: fastest sellers first (most revenue lost per day of empty shelf)
    critical_n = stockout_n // 3
    stockout_rows = pd.concat([
        top(("STOCKOUT",), velocity, stockout_n - critical_n),
        top(("CRITICAL",), velocity, critical_n),
    ])
    stockout_rows = stockout_rows.loc[velocity.loc[stockout_rows.index].sort_values(ascending=False, kind="mergesort").index]
    # Overstock: most cash tied up on the shelf first
    overstock_rows = top(("OVERSTOCK",), capital, overstock_n)
    low_rows = top(("AT_RISK",), velocity, low_stock_n)
    ok_rows = top(("HEALTHY",), velocity, available_n)

    items = (
        _interleave(_inventory_records(stockout_rows), _inventory_records(overstock_rows))
        + _inventory_records(low_rows)
        + _inventory_records(ok_rows)
    )

    summary = {
        "total_items": total,
        "available_count": n_ok,
        "low_stock_count": n_low,
        "stockout_count": n_stockout + n_critical,
        "overstock_count": n_over,
        "healthy_pct": round(n_ok / max(total, 1) * 100, 1),
        # extra detail
        "stockout_breakdown": {"STOCKOUT": n_stockout, "CRITICAL": n_critical},
        "displayed_items": len(items),
        "stores": int(frame["store_id"].nunique()),
        "source": "Rio Mart Unified Dataset",
        "demand_basis": "Predicted demand = daily demand x festival multiplier x supplier lead time",
        "note": (
            f"Showing the {len(items)} highest-priority items out of {total:,} store/SKU records "
            f"({n_stockout + n_critical:,} stockout-risk, {n_over:,} overstock)."
        ),
    }
    return items, summary


# --------------------------------------------------------------------------- #
# Wastage Agent view: near-expiry items with discounts (never expired ones)
# --------------------------------------------------------------------------- #
def _wastage_records(rows: pd.DataFrame) -> List[Dict[str, Any]]:
    today = _today()
    records: List[Dict[str, Any]] = []
    for _, r in rows.iterrows():
        days = int(r["days_to_nearest_expiry"])
        pct = int(r["near_expiry_discount_pct"])
        mrp = float(r["mrp"]) if pd.notna(r.get("mrp")) else 0.0
        disc_price = float(r["near_expiry_discounted_price"]) if pd.notna(r["near_expiry_discounted_price"]) else mrp
        cost = float(r["unit_cost"]) if pd.notna(r.get("unit_cost")) else 0.0
        stock = int(r["current_stock"])
        batch_qty = int(r["nearest_batch_quantity"]) if pd.notna(r.get("nearest_batch_quantity")) else stock
        batch_id = _clean(r.get("nearest_batch_id"))
        units_at_risk = min(stock, batch_qty) if batch_qty > 0 else stock
        expiry = today + timedelta(days=days)
        records.append({
            "product_id": _product_id(r),
            "product_name": str(r.get("product_name", "")),
            "category": _clean(r.get("sub_cat_name")),
            "expiry_date": expiry.strftime("%Y-%m-%d"),
            "days_remaining": days,
            "decision": "Apply Discount",
            "discount": f"{pct}%",
            "discount_pct": pct,
            "mrp": round(mrp, 2),
            "discounted_price": round(disc_price, 2),
            "reason": (
                f"Near expiry: {days} day(s) left"
                f"{' (batch ' + str(batch_id) + ')' if batch_id else ''}. "
                f"Apply {pct}% markdown: MRP ₹{mrp:,.2f} -> ₹{disc_price:,.2f}."
            ),
            "unit_cost": f"₹{cost:.2f}",
            "current_stock": stock,
            "batch_id": batch_id,
            "batch_quantity": batch_qty,
            "units_at_risk": units_at_risk,
            "value_at_risk_inr": round(units_at_risk * cost, 2),
            "warehouse": str(r.get("store_name", r["store_id"])),
            "store_id": str(r["store_id"]),
        })
    return records


def build_wastage_view(
    df: pd.DataFrame, per_tier: int = 20, already_enriched: bool = False
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Builds the Wastage Agent output: near-expiry perishable items, each with a discount,
    balanced across discount tiers and ranked by rupee value at risk. Expired items are
    never returned; the summary counts them so a stale dataset would still be noticed.
    """
    frame = _prepare(df, already_enriched)
    perishable = _perishable_mask(frame)
    days = _num(frame, "days_to_nearest_expiry", default=None)
    near = near_expiry_mask(frame)
    expired_count = int((perishable & days.notna() & (days < 0)).sum())

    cost = _num(frame, "unit_cost").fillna(0)
    stock = _num(frame, "current_stock").fillna(0)
    batch_qty = _num(frame, "nearest_batch_quantity", default=None).fillna(stock)
    at_risk_units = np.minimum(stock, batch_qty.where(batch_qty > 0, stock))
    value = at_risk_units * cost

    near_idx = frame.index[near]
    near_days = days.loc[near_idx]
    tier_bounds = [(-1, 2), (2, 5), (5, 7), (7, 10_000)]
    chosen_idx: List[Any] = []
    for lo, hi in tier_bounds:
        idx = near_days.index[(near_days > lo) & (near_days <= hi)]
        best = value.loc[idx].sort_values(ascending=False, kind="mergesort").head(per_tier)
        chosen_idx.extend(best.index.tolist())
    chosen = frame.loc[chosen_idx]
    order = pd.DataFrame({"d": days.loc[chosen_idx], "v": -value.loc[chosen_idx]}).sort_values(["d", "v"], kind="mergesort")
    chosen = frame.loc[order.index]
    decisions = _wastage_records(chosen)

    n_perishable = int(perishable.sum())
    n_near = int(near.sum())
    normal = max(n_perishable - n_near - expired_count, 0)
    avg_discount = float(frame.loc[near, "near_expiry_discount_pct"].mean()) if n_near else 0.0
    summary = {
        "total_products": n_perishable,
        "near_expiry_count": n_near,
        "discount_count": n_near,
        "expired_count": expired_count,
        "normal_count": normal,
        "near_expiry_pct": round(n_near / max(n_perishable, 1) * 100, 1),
        # extra detail
        "avg_discount_pct": round(avg_discount, 1),
        "value_at_risk_inr": round(float(value.loc[near_idx].sum()), 2),
        "discount_tiers": [{"max_days": t, "discount_pct": p} for t, p in DISCOUNT_TIERS],
        "displayed_items": len(decisions),
        "source": "Rio Mart Unified Dataset",
        "note": (
            f"Showing the {len(decisions)} most valuable near-expiry items out of {n_near:,} "
            f"flagged across {int(frame['store_id'].nunique())} stores."
        ),
    }
    return decisions, summary
