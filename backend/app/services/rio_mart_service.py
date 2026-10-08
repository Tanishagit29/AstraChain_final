import os
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from app.core.logging import logger
from app.services.rio_mart_intelligence import (
    enrich_rio_mart_frame,
    build_inventory_view,
    build_wastage_view,
    near_expiry_mask,
    safe_int,
    safe_float,
    safe_str,
)

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Rio_Mart_Unified.csv")


class RioMartService:
    _df: Optional[pd.DataFrame] = None

    @classmethod
    def _load_data(cls) -> pd.DataFrame:
        if cls._df is None:
            resolved_path = os.path.abspath(CSV_PATH)
            if not os.path.exists(resolved_path):
                logger.error(f"Rio Mart CSV file not found at: {resolved_path}")
                raise FileNotFoundError(f"Rio Mart dataset not found at {resolved_path}")
            
            logger.info(f"Loading Rio Mart Unified Dataset from {resolved_path}...")
            # Optimization: load with optimal dtypes
            df = pd.read_csv(resolved_path, low_memory=False)
            
            # Clean string columns
            string_cols = ['store_id', 'store_name', 'area', 'product_name', 'sub_cat_name', 
                           'stockout_risk', 'perishable_tier', 'festival_groups', 'next_festival_name', 'wastage_flag']
            for col in string_cols:
                if col in df.columns:
                    df[col] = df[col].fillna("").astype(str)

            # Ensure product names are formatted with their sub category
            if 'product_name' in df.columns and 'sub_cat_name' in df.columns:
                def format_prod_name(row):
                    p_name = str(row['product_name']).strip()
                    sub_cat = str(row['sub_cat_name']).strip()
                    if sub_cat and sub_cat.lower() != 'nan' and sub_cat.lower() not in p_name.lower():
                        return f"{p_name} ({sub_cat})"
                    return p_name
                df['product_name'] = df.apply(format_prod_name, axis=1)

            # Clean numeric columns
            num_cols = ['latitude', 'longitude', 'demand_weight', 'unit_cost', 'mrp', 'unit_weight_kg',
                        'avg_daily_demand_units', 'recent_avg_daily_units_per_store',
                        'expected_next_festival_multiplier', 'current_stock', 'reorder_point_units',
                        'safety_stock_units', 'max_stock_units', 'lead_time_days', 'days_of_cover',
                        'days_to_nearest_expiry', 'store_delivery_units_today', 'store_delivery_weight_kg_today']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            if 'is_perishable' in df.columns:
                df['is_perishable'] = df['is_perishable'].astype(str).str.lower().isin(['true', '1', 'yes'])

            # Ensure unique columns
            df = df.loc[:, ~df.columns.duplicated()]

            # Stockout + OVERSTOCK status and near-expiry discounts. Idempotent, so it is a
            # no-op for a CSV that was already enriched by scripts/enrich_rio_mart_csv.py.
            df = enrich_rio_mart_frame(df, copy=False)

            cls._df = df
            logger.info(f"Rio Mart Unified Dataset loaded successfully with {len(cls._df)} records.")
        return cls._df

    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        df = cls._load_data()
        
        total_records = len(df)
        total_stores = safe_int(df['store_id'].nunique()) if 'store_id' in df.columns else 0
        total_products = safe_int(df['product_code'].nunique()) if 'product_code' in df.columns else 0
        total_stock_units = safe_int(df['current_stock'].sum()) if 'current_stock' in df.columns else 0
        total_inventory_val = safe_float((df['current_stock'] * df['unit_cost']).sum()) if ('current_stock' in df.columns and 'unit_cost' in df.columns) else 0.0
        
        stockout_counts = df['stockout_risk'].value_counts().to_dict() if 'stockout_risk' in df.columns else {}
        perishable_count = safe_int(df['is_perishable'].sum()) if 'is_perishable' in df.columns else 0
        wastage_flag_counts = df['wastage_flag'].value_counts().to_dict() if 'wastage_flag' in df.columns else {}
        near_expiry_discounted = safe_int(near_expiry_mask(df).sum())
        
        categories = df['sub_cat_name'].nunique() if 'sub_cat_name' in df.columns else 0
        
        return {
            "dataset": "Rio Mart Unified Dataset",
            "total_records": total_records,
            "total_stores": total_stores,
            "total_unique_products": total_products,
            "total_categories": safe_int(categories),
            "total_stock_units": total_stock_units,
            "total_inventory_valuation_inr": round(total_inventory_val, 2),
            "stockout_risk_breakdown": stockout_counts,
            "perishable_skus": perishable_count,
            "wastage_flag_breakdown": wastage_flag_counts,
            "near_expiry_discounted_skus": near_expiry_discounted,
            "upcoming_festivals": df['next_festival_name'].unique().tolist() if 'next_festival_name' in df.columns else []
        }

    @classmethod
    def get_stores(cls) -> List[Dict[str, Any]]:
        df = cls._load_data()
        store_cols = ['store_id', 'store_name', 'area', 'latitude', 'longitude', 
                      'demand_weight', 'store_delivery_units_today', 'store_delivery_weight_kg_today']
        available = [c for c in store_cols if c in df.columns]
        
        grouped = df.groupby(['store_id', 'store_name', 'area']).agg({
            'latitude': 'first',
            'longitude': 'first',
            'demand_weight': 'first',
            'product_code': 'count',
            'current_stock': 'sum',
            'store_delivery_units_today': 'first',
            'store_delivery_weight_kg_today': 'first'
        }).reset_index()
        
        stores = []
        for _, row in grouped.iterrows():
            stores.append({
                "store_id": safe_str(row['store_id']),
                "store_name": safe_str(row['store_name']),
                "area": safe_str(row['area']),
                "latitude": safe_float(row['latitude']),
                "longitude": safe_float(row['longitude']),
                "demand_weight": safe_float(row['demand_weight']),
                "total_skus": safe_int(row['product_code']),
                "total_stock": safe_int(row['current_stock']),
                "store_delivery_units_today": safe_int(row['store_delivery_units_today']),
                "store_delivery_weight_kg_today": safe_float(row['store_delivery_weight_kg_today'])
            })
        return stores

    @classmethod
    def get_inventory(
        cls,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        store_id: Optional[str] = None,
        category: Optional[str] = None,
        risk: Optional[str] = None,
        is_perishable: Optional[bool] = None,
        festival: Optional[str] = None
    ) -> Dict[str, Any]:
        df = cls._load_data()
        filtered = df.copy()

        if store_id:
            filtered = filtered[filtered['store_id'].str.lower() == store_id.lower()]
        if search:
            s = search.lower()
            filtered = filtered[
                filtered['product_name'].str.lower().str.contains(s) |
                filtered['product_code'].astype(str).str.lower().str.contains(s) |
                filtered['sub_cat_name'].str.lower().str.contains(s)
            ]
        if category:
            filtered = filtered[filtered['sub_cat_name'].str.lower().str.contains(category.lower())]
        if risk:
            filtered = filtered[filtered['stockout_risk'].str.upper() == risk.upper()]
        if is_perishable is not None:
            filtered = filtered[filtered['is_perishable'] == is_perishable]
        if festival:
            filtered = filtered[filtered['next_festival_name'].str.lower().str.contains(festival.lower()) | filtered['festival_groups'].str.lower().str.contains(festival.lower())]

        total = len(filtered)
        start = (page - 1) * limit
        end = start + limit
        sliced = filtered.iloc[start:end]

        items = sliced.to_dict(orient='records')
        
        # Format JSON response types cleanly
        cleaned_items = []
        for item in items:
            cleaned = {}
            for k, v in item.items():
                if pd.isna(v):
                    cleaned[k] = None
                elif isinstance(v, (pd.Series, np.ndarray)):
                    cleaned[k] = safe_int(v) if isinstance(v, (int, np.integer)) else safe_float(v)
                elif isinstance(v, (np.integer, int)):
                    cleaned[k] = safe_int(v)
                elif isinstance(v, (np.floating, float)):
                    cleaned[k] = safe_float(v) if not np.isnan(v) else None
                else:
                    cleaned[k] = safe_str(v) if not isinstance(v, (dict, list, bool)) else v
            cleaned_items.append(cleaned)

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit > 0 else 1,
            "items": cleaned_items
        }

    @classmethod
    def get_festivals_impact(cls) -> List[Dict[str, Any]]:
        df = cls._load_data()
        if 'next_festival_name' not in df.columns:
            return []
        
        grouped = df.groupby('next_festival_name').agg({
            'product_code': 'count',
            'expected_next_festival_multiplier': 'mean',
            'avg_daily_demand_units': 'sum',
            'current_stock': 'sum'
        }).reset_index()

        festivals = []
        for _, row in grouped.iterrows():
            f_name = safe_str(row['next_festival_name'])
            if not f_name or f_name == 'nan':
                continue
            baseline = safe_float(row['avg_daily_demand_units'], 0.0)
            mult = safe_float(row['expected_next_festival_multiplier'], 1.0)
            projected = round(baseline * mult, 2)
            
            festivals.append({
                "festival_name": f_name,
                "affected_skus": safe_int(row['product_code']),
                "avg_demand_multiplier": round(mult, 2),
                "total_daily_baseline_demand": round(baseline, 2),
                "projected_daily_festival_demand": projected,
                "current_total_stock": safe_int(row['current_stock'])
            })
        return festivals

    @classmethod
    def get_inventory_agent_view(cls) -> Dict[str, Any]:
        """Inventory Agent output: stockout AND overstock items + dataset-wide counts."""
        items, summary = build_inventory_view(cls._load_data(), already_enriched=True)
        return {"summary": summary, "items": items}

    @classmethod
    def get_wastage_agent_view(cls) -> Dict[str, Any]:
        """Wastage Agent output: near-expiry items with a discount each (no expired items)."""
        decisions, summary = build_wastage_view(cls._load_data(), already_enriched=True)
        return {"summary": summary, "decisions": decisions}

    @classmethod
    def get_wastage_risk_items(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """Near-expiry perishables (most urgent first) with their recommended discount."""
        df = cls._load_data()
        near = df[near_expiry_mask(df)].copy()
        if len(near) == 0:
            return []

        near['_value'] = near['current_stock'] * near['unit_cost']
        near = near.sort_values(by=['days_to_nearest_expiry', '_value'], ascending=[True, False]).head(limit)
        near = near.drop(columns=['_value'])

        items = near.to_dict(orient='records')
        cleaned_items = []
        for item in items:
            cleaned = {}
            for k, v in item.items():
                if pd.isna(v):
                    cleaned[k] = None
                elif isinstance(v, (pd.Series, np.ndarray)):
                    cleaned[k] = safe_int(v) if isinstance(v, (int, np.integer)) else safe_float(v)
                elif isinstance(v, (np.integer, int)):
                    cleaned[k] = safe_int(v)
                elif isinstance(v, (np.floating, float)):
                    cleaned[k] = safe_float(v) if not np.isnan(v) else None
                else:
                    cleaned[k] = safe_str(v) if not isinstance(v, (dict, list, bool)) else v
            cleaned_items.append(cleaned)
        return cleaned_items
