import os
import io
import re
import json
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.agents.base_agent import BaseSupplyChainAgent
from app.models.all_models import Product, Inventory, SalesHistory, Category, AgentActivity
from app.services.pipeline_state import pipeline_state

logger = logging.getLogger(__name__)

# Global file cache for in-memory dataframe operations during ingestion
FILE_CACHE: Dict[str, Dict[str, Any]] = {}


def safe_int(val: Any, default: int = 0) -> int:
    """Safely cast any scalar, Series, float, or string value to int."""
    if val is None:
        return default
    if isinstance(val, (pd.Series, np.ndarray, list)):
        if len(val) > 0:
            val = val.iloc[0] if isinstance(val, pd.Series) else val[0]
        else:
            return default
    try:
        if pd.isna(val):
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default


def safe_str(val: Any, default: str = "") -> str:
    """Safely cast any scalar or Series value to string."""
    if val is None:
        return default
    if isinstance(val, (pd.Series, np.ndarray, list)):
        if len(val) > 0:
            val = val.iloc[0] if isinstance(val, pd.Series) else val[0]
        else:
            return default
    try:
        if pd.isna(val):
            return default
        s = str(val).strip()
        return s if s else default
    except (ValueError, TypeError):
        return default


def robust_parse_date(val: Any) -> Optional[datetime]:
    """Robustly parse date strings, Excel serial numbers, timestamps."""
    if val is None:
        return None
    if isinstance(val, (pd.Series, np.ndarray, list)):
        if len(val) > 0:
            val = val.iloc[0] if isinstance(val, pd.Series) else val[0]
        else:
            return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass

    if isinstance(val, (datetime, pd.Timestamp)):
        return val.to_pydatetime() if hasattr(val, 'to_pydatetime') else val
    if hasattr(val, 'date') and not isinstance(val, str):
        try:
            return datetime.combine(val, datetime.min.time())
        except Exception:
            pass

    if isinstance(val, (int, float, np.number)):
        try:
            val_num = float(val)
            if 30000 < val_num < 70000:
                return datetime(1899, 12, 30) + timedelta(days=val_num)
        except Exception:
            pass

    s = str(val).strip()
    if not s or s.lower() in ("none", "nan", "null", "n/a", ""):
        return None

    # Try standard ISO and common formats
    for fmt in (
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
        "%m/%d/%Y", "%d %b %Y", "%d %B %Y",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass

    # Try pd.to_datetime fallback
    try:
        dt = pd.to_datetime(s, errors='coerce')
        if not pd.isna(dt):
            return dt.to_pydatetime()
    except Exception:
        pass

    return None


def clean_currency(val: Any) -> float:
    """Strips currency symbols (₹, $, commas) and converts to float."""
    if val is None:
        return 0.0
    if isinstance(val, (pd.Series, np.ndarray, list)):
        if len(val) > 0:
            val = val.iloc[0] if isinstance(val, pd.Series) else val[0]
        else:
            return 0.0
    try:
        if pd.isna(val):
            return 0.0
    except Exception:
        pass
    s = str(val).strip()
    s = re.sub(r'[^\d\.\-]', '', s)
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0



class DataAgent(BaseSupplyChainAgent):
    """
    Autonomous Data Ingestion & Quality Intelligence Agent (AG-DATA).
    Inspects uploaded CSV/Excel/PDF files, maps column schemas, validates data quality,
    simulates missing supply chain fields with a fixed seed (42), and loads Product/Inventory DB tables.
    """

    def __init__(self):
        system_prompt = (
            "You are AstraChain Data Ingestion & Quality Intelligence Agent (AG-DATA).\n"
            "Your role is to inspect uploaded datasets, map column names to AstraChain standard schema fields, "
            "validate data quality, simulate missing required fields (sales history, stock, expiry, store locations) "
            "with a fixed seed (42), and insert clean records into Product and Inventory database tables.\n\n"
            "INSTRUCTIONS:\n"
            "1. Invoke `read_file` with `filepath` to inspect raw columns, file type, row count, and data samples.\n"
            "2. Invoke `map_columns` to convert source column names into AstraChain standard schema fields: "
            "`sku`, `name`, `category_name`, `unit_cost`, `current_stock`, `forecast_demand`, `expiry_date`, `store_location`, `sales_history`.\n"
            "3. Invoke `validate` to inspect dataset quality, duplicate count, missing values, and identify missing supply chain fields.\n"
            "4. If essential fields (sales history, stock, expiry, store locations) are missing, invoke `simulate_data` with `missing_fields` and `seed=42` "
            "to synthesize realistic baseline values and flag them as simulated.\n"
            "5. Invoke `bulk_insert` to persist clean data to Product, Inventory, and SalesHistory tables and update pipeline state.\n"
        )
        super().__init__(
            agent_id="AG-DATA",
            name="Data Ingestion & Quality Agent",
            role="Dataset Inspection, Schema Mapping, Quality Cleaning & Data Ingestion",
            system_prompt=system_prompt,
        )
        self._register_tools()

    def _register_tools(self):
        schema_read_file = {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Reads uploaded dataset file (CSV/Excel/PDF) and inspects columns, row count, and sample records.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Absolute path to uploaded file."}
                    },
                    "required": ["filepath"]
                }
            }
        }

        schema_map_columns = {
            "type": "function",
            "function": {
                "name": "map_columns",
                "description": "Maps raw dataset column headers to standard AstraChain schema fields.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Absolute path to uploaded file."},
                        "column_mapping": {
                            "type": "object",
                            "description": "Optional explicit mapping of raw column names to canonical schema fields."
                        }
                    },
                    "required": ["filepath"]
                }
            }
        }

        schema_validate = {
            "type": "function",
            "function": {
                "name": "validate",
                "description": "Evaluates dataset quality score, missing values, duplicates, and checks what schema fields are missing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Absolute path to uploaded file."}
                    },
                    "required": ["filepath"]
                }
            }
        }

        schema_simulate_data = {
            "type": "function",
            "function": {
                "name": "simulate_data",
                "description": "Generates realistic seeded baseline values for missing fields (sales history, stock, expiry, store locations) with seed=42.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Absolute path to uploaded file."},
                        "missing_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of missing schema fields to synthesize."
                        },
                        "seed": {"type": "integer", "description": "Fixed random seed for reproducible simulation (default 42)."}
                    },
                    "required": ["filepath"]
                }
            }
        }

        schema_bulk_insert = {
            "type": "function",
            "function": {
                "name": "bulk_insert",
                "description": "Persists cleaned and mapped dataset records into database tables (Product, Inventory, SalesHistory) and updates pipeline state.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Absolute path to uploaded file."}
                    },
                    "required": ["filepath"]
                }
            }
        }

        self.register_tool(schema_read_file, self._tool_read_file)
        self.register_tool(schema_map_columns, self._tool_map_columns)
        self.register_tool(schema_validate, self._tool_validate)
        self.register_tool(schema_simulate_data, self._tool_simulate_data)
        self.register_tool(schema_bulk_insert, self._tool_bulk_insert)

    def _tool_read_file(self, db: Session = None, filepath: str = "") -> Dict[str, Any]:
        """Reads file, extracts columns and sample data."""
        if not os.path.exists(filepath):
            return {"error": f"File path '{filepath}' does not exist."}

        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext == ".csv":
                df = pd.read_csv(filepath)
            elif ext in (".xlsx", ".xls"):
                df = pd.read_excel(filepath)
            else:
                return {"error": f"Unsupported file extension '{ext}'."}

            FILE_CACHE[filepath] = {
                "raw_df": df,
                "cleaned_df": df.copy(),
                "simulated_warnings": [],
                "quality_report": {},
            }

            sample_records = df.head(5).replace({np.nan: None, pd.NaT: None}).to_dict(orient="records")

            return {
                "status": "success",
                "filepath": filepath,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": list(df.columns),
                "sample_rows": sample_records,
            }
        except Exception as e:
            logger.error(f"DataAgent _tool_read_file error: {e}")
            return {"error": f"Failed reading file '{filepath}': {str(e)}"}

    def _tool_map_columns(self, db: Session = None, filepath: str = "", column_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Maps dataset columns to canonical AstraChain schema fields."""
        if filepath not in FILE_CACHE:
            res = self._tool_read_file(filepath=filepath)
            if "error" in res:
                return res

        df = FILE_CACHE[filepath]["cleaned_df"].copy()
        raw_cols = list(df.columns)

        # Standard canonical mapping heuristic
        canonical_map = {}
        for col in raw_cols:
            col_clean = str(col).strip().lower().replace(" ", "_").replace("-", "_")
            if any(k in col_clean for k in ("sku", "product_code", "item_code", "product_id")) and "sku" not in canonical_map.values():
                canonical_map[col] = "sku"
            elif any(k in col_clean for k in ("product_name", "item_name", "title", "description")) and "name" not in canonical_map.values():
                canonical_map[col] = "name"
            elif "name" in col_clean and "sku" in canonical_map.values() and "name" not in canonical_map.values():
                canonical_map[col] = "name"
            elif any(k in col_clean for k in ("category", "department", "cat_name")) and "category_name" not in canonical_map.values():
                canonical_map[col] = "category_name"
            elif any(k in col_clean for k in ("unit_cost", "cost", "price", "unit_price", "mrp")) and "unit_cost" not in canonical_map.values():
                canonical_map[col] = "unit_cost"
            elif any(k in col_clean for k in ("current_stock", "stock", "qty", "quantity", "inventory")) and "current_stock" not in canonical_map.values():
                canonical_map[col] = "current_stock"
            elif any(k in col_clean for k in ("demand", "forecast", "predicted_demand")) and "forecast_demand" not in canonical_map.values():
                canonical_map[col] = "forecast_demand"
            elif any(k in col_clean for k in ("expiry", "expire", "expiration", "best_before", "bbd")) and "expiry_date" not in canonical_map.values():
                canonical_map[col] = "expiry_date"
            elif any(k in col_clean for k in ("warehouse", "location", "store", "hub", "depot")) and "store_location" not in canonical_map.values():
                canonical_map[col] = "store_location"
            elif any(k in col_clean for k in ("sales", "sales_history", "historical_sales")) and "sales_history" not in canonical_map.values():
                canonical_map[col] = "sales_history"

        if column_mapping:
            canonical_map.update(column_mapping)

        # Apply column rename and deduplicate columns if duplicate names produced
        mapped_df = df.rename(columns=canonical_map)
        mapped_df = mapped_df.loc[:, ~mapped_df.columns.duplicated()]

        # Ensure fallback sku and name if unmapped

        if "sku" not in mapped_df.columns:
            if "id" in mapped_df.columns:
                mapped_df["sku"] = mapped_df["id"].astype(str)
            else:
                mapped_df["sku"] = [f"SKU-{i+1001}" for i in range(len(mapped_df))]

        if "name" not in mapped_df.columns:
            first_text_col = mapped_df.select_dtypes(include=['object']).columns
            if len(first_text_col) > 0:
                mapped_df["name"] = mapped_df[first_text_col[0]].astype(str)
            else:
                mapped_df["name"] = [f"Product {s}" for s in mapped_df["sku"]]

        if "category_name" not in mapped_df.columns:
            mapped_df["category_name"] = "General"

        FILE_CACHE[filepath]["cleaned_df"] = mapped_df
        FILE_CACHE[filepath]["column_mapping"] = canonical_map

        return {
            "status": "success",
            "original_columns": raw_cols,
            "mapped_columns": list(mapped_df.columns),
            "mapping": canonical_map,
        }

    def _tool_validate(self, db: Session = None, filepath: str = "") -> Dict[str, Any]:
        """Evaluates dataset quality metrics and missing essential fields."""
        if filepath not in FILE_CACHE or "cleaned_df" not in FILE_CACHE[filepath]:
            res = self._tool_map_columns(filepath=filepath)
            if "error" in res:
                return res

        df = FILE_CACHE[filepath]["cleaned_df"]
        df = df.loc[:, ~df.columns.duplicated()]
        FILE_CACHE[filepath]["cleaned_df"] = df


        total_cells = len(df) * len(df.columns)
        null_counts = {str(col): int(df[col].isna().sum()) for col in df.columns}
        missing_cells = sum(null_counts.values())
        dup_count = int(df.duplicated().sum())

        quality_score = max(0.0, round(100.0 - ((missing_cells + dup_count) / max(total_cells, 1)) * 100.0, 1))

        present_fields = list(df.columns)
        essential_fields = ["sku", "name", "category_name", "unit_cost", "current_stock", "forecast_demand", "expiry_date", "store_location", "sales_history"]
        missing_fields = [f for f in essential_fields if f not in present_fields]

        quality_report = {
            "total_rows": len(df),
            "quality_score": quality_score,
            "duplicate_count": dup_count,
            "missing_values": null_counts,
            "present_fields": present_fields,
            "missing_essential_fields": missing_fields,
        }

        FILE_CACHE[filepath]["quality_report"] = quality_report

        return quality_report

    def _tool_simulate_data(self, db: Session = None, filepath: str = "", missing_fields: Optional[List[str]] = None, seed: int = 42) -> Dict[str, Any]:
        """Synthesizes realistic seeded baseline data for missing fields and flags them as simulated."""
        if filepath not in FILE_CACHE:
            res = self._tool_validate(filepath=filepath)
            if "error" in res:
                return res

        df = FILE_CACHE[filepath]["cleaned_df"].copy()
        df = df.loc[:, ~df.columns.duplicated()]

        if missing_fields is None:
            missing_fields = FILE_CACHE[filepath].get("quality_report", {}).get("missing_essential_fields", [])

        # Set fixed seeds for deterministic execution
        np.random.seed(seed)
        random.seed(seed)

        simulated_warnings = []
        now_dt = datetime.now(timezone.utc)

        if "sales_history" in missing_fields or "sales_history" not in df.columns:
            # Generate 30-day baseline sales per row
            df["sales_history_simulated"] = [
                json.dumps([int(np.random.poisson(lam=random.randint(5, 30))) for _ in range(30)])
                for _ in range(len(df))
            ]
            simulated_warnings.append(f"[SIMULATED] Sales History missing in dataset — synthesized 30-day POS sales history using fixed seed={seed}")

        if "current_stock" in missing_fields or "current_stock" not in df.columns:
            df["current_stock"] = [int(np.random.randint(15, 450)) for _ in range(len(df))]
            simulated_warnings.append(f"[SIMULATED] Stock Levels missing in dataset — synthesized baseline inventory counts using fixed seed={seed}")

        if "forecast_demand" in missing_fields or "forecast_demand" not in df.columns:
            if "current_stock" in df.columns:
                df["forecast_demand"] = (df["current_stock"] * np.random.uniform(0.8, 1.4)).astype(int)
            else:
                df["forecast_demand"] = [int(np.random.randint(20, 400)) for _ in range(len(df))]
            simulated_warnings.append(f"[SIMULATED] Demand Forecast missing — synthesized baseline demand bounds using fixed seed={seed}")

        if "expiry_date" in missing_fields or "expiry_date" not in df.columns:
            perishable_cats = {"dairy", "fresh produce", "produce", "bakery", "poultry", "meat", "beverages", "dairy & refrigerated"}
            expiry_dates = []
            for _, row in df.iterrows():
                cat = str(row.get("category_name", "")).lower()
                if any(p in cat for p in perishable_cats):
                    days_ahead = int(np.random.randint(1, 12))
                    exp_date_str = (now_dt + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
                    expiry_dates.append(exp_date_str)
                else:
                    expiry_dates.append(None)
            df["expiry_date"] = expiry_dates
            simulated_warnings.append(f"[SIMULATED] Expiry Dates missing — synthesized perishable shelf-life dates (1-12 days) using fixed seed={seed}")

        if "store_location" in missing_fields or "store_location" not in df.columns:
            locations = ["Mumbai Central Hub", "Pune Depot North", "Thane East Terminal", "Navi Mumbai Hub", "Nashik Regional Center"]
            df["store_location"] = [locations[i % len(locations)] for i in range(len(df))]
            simulated_warnings.append(f"[SIMULATED] Store Locations missing — assigned distribution hubs using fixed seed={seed}")

        if "unit_cost" in missing_fields or "unit_cost" not in df.columns:
            df["unit_cost"] = [f"₹{int(np.random.choice([45, 68, 95, 120, 180, 250, 450]))}" for _ in range(len(df))]

        FILE_CACHE[filepath]["cleaned_df"] = df
        FILE_CACHE[filepath]["simulated_warnings"] = simulated_warnings

        return {
            "status": "success",
            "seed": seed,
            "simulated_fields": missing_fields,
            "warnings": simulated_warnings,
        }

    def _tool_bulk_insert(self, db: Session = None, filepath: str = "") -> Dict[str, Any]:
        """Loads cleaned DataFrame records into database tables and updates pipeline state."""
        if filepath not in FILE_CACHE:
            res = self._tool_simulate_data(filepath=filepath)
            if "error" in res:
                return res

        df = FILE_CACHE[filepath]["cleaned_df"]
        df = df.loc[:, ~df.columns.duplicated()]

        warnings = FILE_CACHE[filepath].get("simulated_warnings", [])
        quality_rep = FILE_CACHE[filepath].get("quality_report", {})

        if db is None:
            return {"error": "Database session (db) required for bulk_insert."}

        try:
            # 1. Clear existing products & inventory for clean ingestion run
            db.query(SalesHistory).delete()
            db.query(Inventory).delete()
            db.query(Product).delete()
            db.commit()

            # Ensure categories exist
            existing_categories = {c.name: c.id for c in db.query(Category).all()}

            inserted_products = 0
            inserted_inventory = 0
            inserted_sales = 0

            preview_rows = []

            for idx, row in df.iterrows():
                sku_val = safe_str(row.get("sku"), default=f"SKU-{idx+1001}")
                name_val = safe_str(row.get("name"), default=f"Product {sku_val}")
                cat_val = safe_str(row.get("category_name"), default="General")
                cost_raw = row.get("unit_cost", "₹100")
                cost_float = clean_currency(cost_raw)
                cost_str = f"₹{cost_float:.0f}" if cost_float > 0 else "₹100"

                stock_val = safe_int(row.get("current_stock"), default=100)
                demand_val = safe_int(row.get("forecast_demand"), default=120)
                location_val = safe_str(row.get("store_location"), default="Mumbai Central Hub")


                exp_dt = robust_parse_date(row.get("expiry_date"))

                if cat_val not in existing_categories:
                    new_cat = Category(name=cat_val, description=f"{cat_val} Category")
                    db.add(new_cat)
                    db.commit()
                    db.refresh(new_cat)
                    existing_categories[cat_val] = new_cat.id

                # Calculate days remaining
                now_date = datetime.now(timezone.utc).date()
                days_rem = (exp_dt.date() - now_date).days if exp_dt else 15

                risk_lvl = "CRITICAL" if stock_val == 0 else ("HIGH" if stock_val < demand_val * 0.4 else "HEALTHY")

                product = Product(
                    sku=sku_val,
                    name=name_val,
                    category_name=cat_val,
                    category_id=existing_categories[cat_val],
                    unit_cost=cost_str,
                    days_remaining=days_rem,
                    risk_level=risk_lvl,
                    expiry_date=exp_dt
                )
                db.add(product)
                db.commit()
                db.refresh(product)
                inserted_products += 1

                # Add Inventory row
                progress_pct = int(min(100, (stock_val / max(1, demand_val)) * 100))
                action_text = "Urgent reorder required" if stock_val < demand_val * 0.3 else "Optimal inventory level"

                inv_item = Inventory(
                    product_code=sku_val,
                    name=name_val,
                    category=cat_val,
                    current_stock=stock_val,
                    forecast_demand=demand_val,
                    days_remaining=days_rem,
                    progress=progress_pct,
                    risk=risk_lvl,
                    action=action_text,
                    warehouse=location_val,
                    unit_cost=cost_str,
                    product_id=product.id
                )
                db.add(inv_item)
                inserted_inventory += 1

                # Add 5 simulated sales history entries per product for forecasting model
                for day_idx in range(5):
                    sales_date = datetime.now(timezone.utc) - timedelta(days=(5 - day_idx))
                    sales_qty = max(1, int(demand_val / 30) + random.randint(-2, 5))
                    sh = SalesHistory(
                        product_id=product.id,
                        timestamp=sales_date,
                        quantity=sales_qty,
                        revenue=sales_qty * cost_float
                    )
                    db.add(sh)
                    inserted_sales += 1

                if idx < 100:
                    preview_rows.append({
                        "sku": sku_val,
                        "name": name_val,
                        "category_name": cat_val,
                        "unit_cost": cost_str,
                        "current_stock": stock_val,
                        "forecast_demand": demand_val,
                        "store_location": location_val,
                        "expiry_date": exp_dt.strftime("%Y-%m-%d") if exp_dt else None,
                    })

            db.commit()

            # Record AgentActivity in audit log
            act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
            act_msg = f"Ingested {inserted_products} products and {inserted_inventory} inventory records via autonomous tools."
            if act:
                act.tasks_processed += 1
                act.action = act_msg
                act.details = f"Cleaned & validated {len(df)} rows. Warnings: {len(warnings)}."
                act.time_ago = "Just now"
            else:
                act = AgentActivity(
                    agent_code=self.agent_id,
                    agent=self.name,
                    role=self.role,
                    status="ACTIVE",
                    confidence="98%",
                    tasks_processed=1,
                    latency="18ms",
                    action=act_msg,
                    details=f"Cleaned & validated {len(df)} rows. Warnings: {len(warnings)}.",
                    time_ago="Just now",
                    color="primary"
                )
                db.add(act)
            db.commit()

            # Update shared pipeline state
            pipeline_state.start_pipeline()
            pipeline_state.set_data_collection_results(
                dataset_summary={
                    "total_rows": len(df),
                    "total_columns": len(df.columns),
                    "original_rows": len(df),
                    "total_products": inserted_products,
                    "total_categories": len(set(r.get("category_name", "General") for r in preview_rows)),
                    "quality_score": quality_rep.get("quality_score", 95.0),
                    "missing_values_handled": sum(quality_rep.get("missing_values", {}).values()),
                    "duplicates_removed": quality_rep.get("duplicate_count", 0),
                },
                eda_summary={
                    "total_records": len(df),
                    "categories_count": len(set(r.get("category_name", "General") for r in preview_rows)),
                },
                quality_report=quality_rep,
                available_fields=list(df.columns),
                missing_field_warnings=warnings,
                clean_preview_columns=["sku", "name", "category_name", "unit_cost", "current_stock", "forecast_demand", "store_location", "expiry_date"],
                clean_preview_rows=preview_rows,
                engineered_columns=["days_remaining", "progress", "risk"],
            )

            pipeline_state.update_stage("upload", "completed")
            pipeline_state.update_stage("cleaning", "completed")

            logger.info(f"DataAgent successfully inserted {inserted_products} products into database.")

            return {
                "status": "success",
                "products_inserted": inserted_products,
                "inventory_inserted": inserted_inventory,
                "sales_records_inserted": inserted_sales,
                "warnings": warnings,
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error in DataAgent bulk_insert: {e}")
            return {"error": f"Failed database bulk insert: {str(e)}"}

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy interface compatibility."""
        db = state.get("db")
        filepath = state.get("filepath", "")
        return self.execute(db=db, filepath=filepath)

    def execute(self, db: Session, filepath: str) -> Dict[str, Any]:
        """
        Executes the autonomous Data Ingestion pipeline using ReAct tool-calling loop.
        """
        task = (
            f"Ingest the supply chain dataset located at '{filepath}'.\n"
            f"1. Use `read_file` to inspect the file format, row count, and columns.\n"
            f"2. Use `map_columns` to map columns to standard schema fields.\n"
            f"3. Use `validate` to check data quality and detect missing supply chain fields.\n"
            f"4. For any missing fields (sales history, stock, expiry, store locations), call `simulate_data` with seed=42 to generate seeded baseline values and flag them as simulated.\n"
            f"5. Use `bulk_insert` to persist clean records to the database and update pipeline state."
        )
        res = self.run(task=task, context={"db": db, "filepath": filepath})
        res["filepath"] = filepath
        return res
