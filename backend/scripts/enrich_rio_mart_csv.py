"""
Enrich Rio_Mart_Unified.csv for the Inventory Agent and the Wastage Agent.

What it changes
---------------
* `stockout_risk`   - rows that sit at their max-stock ceiling with >= 90 days of cover
                      and were labelled HEALTHY are re-labelled OVERSTOCK.
                      (STOCKOUT / CRITICAL / AT_RISK / HEALTHY are otherwise untouched.)
* NEW columns       - inventory_action, suggested_reorder_qty,
                      near_expiry_discount_pct, near_expiry_discounted_price

Every other value is copied through byte-for-byte (the file is processed as text, so
codes such as HSN numbers are not turned into floats) and CRLF line endings are kept.
The script is idempotent: running it again on an enriched file changes nothing.

Usage (from the backend/ folder)
--------------------------------
    python -m scripts.enrich_rio_mart_csv                       # enrich in place
    python -m scripts.enrich_rio_mart_csv --output enriched.csv # write a copy
"""

import argparse
import os
import sys
import tempfile

import pandas as pd

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.rio_mart_intelligence import (  # noqa: E402
    ENRICHED_COLUMNS,
    enrich_rio_mart_frame,
)

DEFAULT_CSV = os.path.join(BACKEND_DIR, "Rio_Mart_Unified.csv")


def enrich_csv(input_path: str, output_path: str) -> dict:
    # Text copy: original values are re-written exactly as they were read.
    raw = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    # Typed copy: used only to compute the new values.
    typed = pd.read_csv(input_path, low_memory=False)
    before = typed["stockout_risk"].astype(str).str.upper().value_counts().to_dict() if "stockout_risk" in typed else {}

    enriched = enrich_rio_mart_frame(typed)

    raw["stockout_risk"] = enriched["stockout_risk"].astype(str)
    raw["inventory_action"] = enriched["inventory_action"].astype(str)
    raw["suggested_reorder_qty"] = enriched["suggested_reorder_qty"].astype(int).astype(str)
    raw["near_expiry_discount_pct"] = enriched["near_expiry_discount_pct"].astype(int).astype(str)
    raw["near_expiry_discounted_price"] = enriched["near_expiry_discounted_price"].map(
        lambda v: "" if pd.isna(v) else f"{v:.2f}"
    )

    out_dir = os.path.dirname(os.path.abspath(output_path))
    fd, tmp_path = tempfile.mkstemp(suffix=".csv", dir=out_dir)
    os.close(fd)
    try:
        raw.to_csv(tmp_path, index=False, lineterminator="\r\n")
        os.replace(tmp_path, output_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return {
        "rows": len(raw),
        "columns": len(raw.columns),
        "new_columns": ENRICHED_COLUMNS,
        "stockout_risk_before": before,
        "stockout_risk_after": enriched["stockout_risk"].value_counts().to_dict(),
        "near_expiry_discounted_rows": int((enriched["near_expiry_discount_pct"] > 0).sum()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default=DEFAULT_CSV, help="CSV to read (default: backend/Rio_Mart_Unified.csv)")
    parser.add_argument("--output", default=None, help="CSV to write (default: overwrite the input)")
    args = parser.parse_args()

    result = enrich_csv(args.input, args.output or args.input)
    print(f"Enriched {result['rows']:,} rows -> {result['columns']} columns")
    print(f"  stockout_risk before: {result['stockout_risk_before']}")
    print(f"  stockout_risk after : {result['stockout_risk_after']}")
    print(f"  near-expiry rows with a discount: {result['near_expiry_discounted_rows']:,}")
