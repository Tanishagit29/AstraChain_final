"""
Shared Pipeline State Module
============================
Single source of truth for the latest pipeline execution results.
All frontend pages read from this state to display consistent, up-to-date data.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import uuid

from app.services.rio_mart_intelligence import (
    NEAR_EXPIRY_MAX_DAYS,
    discount_pct_for_days,
)


class PipelineState:
    """Singleton-like module-level state holding the latest pipeline results."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all pipeline state to defaults."""
        self.dataset_id: Optional[str] = None
        self.pipeline_timestamp: Optional[datetime] = None
        self.has_run: bool = False

        # Data Collection Agent results
        self.dataset_summary: Dict[str, Any] = {}
        self.eda_summary: Dict[str, Any] = {}
        self.quality_report: Dict[str, Any] = {}
        self.available_fields: List[str] = []
        self.missing_field_warnings: List[str] = []
        self.clean_preview_columns: List[str] = []
        self.clean_preview_rows: List[Dict] = []
        self.engineered_columns: List[str] = []

        # Demand Forecasting Agent results
        self.forecast_results: List[Dict[str, Any]] = []
        self.forecast_by_product: Dict[str, Any] = {}
        self.forecast_model: str = "XGBoost"
        self.forecast_metric: Optional[Dict[str, Any]] = None
        self.forecast_timestamp: Optional[datetime] = None

        # Inventory Analysis Module results
        self.inventory_analysis: List[Dict[str, Any]] = []
        self.inventory_summary: Dict[str, Any] = {}

        # Automation & Wastage Agent results
        self.wastage_decisions: List[Dict[str, Any]] = []
        self.wastage_summary: Dict[str, Any] = {}
        self.expiry_available: bool = False
        # Dataset-wide counts that are not represented by an individual row in wastage_decisions
        # (the decisions list only holds the highest-priority sample of a large dataset).
        self._wastage_offset: Dict[str, int] = {}

        # Pipeline stage status
        self.stages: Dict[str, str] = {
            "upload": "pending",
            "cleaning": "pending",
            "forecasting": "pending",
            "inventory": "pending",
            "wastage": "pending",
        }

    def start_pipeline(self):
        """Mark a new pipeline run starting."""
        self.dataset_id = str(uuid.uuid4())[:12]
        self.pipeline_timestamp = datetime.now(timezone.utc)
        self.has_run = True
        for key in self.stages:
            self.stages[key] = "pending"

    def update_stage(self, stage: str, status: str):
        """Update a pipeline stage status: pending, running, completed, error."""
        if stage in self.stages:
            self.stages[stage] = status

    def set_data_collection_results(
        self,
        dataset_summary: Dict,
        eda_summary: Dict,
        quality_report: Dict,
        available_fields: List[str],
        missing_field_warnings: List[str],
        clean_preview_columns: List[str],
        clean_preview_rows: List[Dict],
        engineered_columns: List[str],
    ):
        self.dataset_summary = dataset_summary
        self.eda_summary = eda_summary
        self.quality_report = quality_report
        self.available_fields = available_fields
        self.missing_field_warnings = missing_field_warnings
        self.clean_preview_columns = clean_preview_columns
        self.clean_preview_rows = clean_preview_rows
        self.engineered_columns = engineered_columns

    def set_forecast_results(
        self,
        forecast_results: List[Dict],
        forecast_by_product: Dict,
        forecast_metric: Optional[Dict] = None,
    ):
        self.forecast_results = forecast_results
        self.forecast_by_product = forecast_by_product
        self.forecast_metric = forecast_metric
        self.forecast_timestamp = datetime.now(timezone.utc)

    def set_inventory_results(
        self,
        inventory_analysis: List[Dict],
        inventory_summary: Dict,
    ):
        self.inventory_analysis = inventory_analysis
        self.inventory_summary = inventory_summary

    def set_wastage_results(
        self,
        wastage_decisions: List[Dict],
        wastage_summary: Dict,
        expiry_available: bool,
    ):
        self.wastage_decisions = wastage_decisions
        self.wastage_summary = wastage_summary
        self.expiry_available = expiry_available
        self._wastage_offset = {}

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Compile data for the overview dashboard."""
        if not self.has_run:
            return {"has_data": False}

        return {
            "has_data": True,
            "dataset_id": self.dataset_id,
            "pipeline_timestamp": self.pipeline_timestamp.isoformat() if self.pipeline_timestamp else None,
            "stages": self.stages,
            "dataset_summary": self.dataset_summary,
            "forecast_summary": {
                "model": self.forecast_model,
                "timestamp": self.forecast_timestamp.isoformat() if self.forecast_timestamp else None,
                "total_predictions": len(self.forecast_results),
                "metric": self.forecast_metric,
            },
            "inventory_summary": self.inventory_summary,
            "wastage_summary": self.wastage_summary,
            "missing_field_warnings": self.missing_field_warnings,
        }

    def add_near_expiry_item(
        self,
        product_name: str,
        product_id: Optional[str] = None,
        category: str = "General",
        days_remaining: int = 3,
        expiry_date: Optional[str] = None,
        discount_override: Optional[str] = None,
        unit_cost: str = "₹100",
        current_stock: int = 100,
        warehouse: str = "Main Terminal"
    ) -> Dict[str, Any]:
        """Dynamically add a near-to-expire item with automatic discount rules to pipeline state."""
        self.has_run = True
        self.expiry_available = True
        if not self.dataset_id:
            self.dataset_id = str(uuid.uuid4())[:12]
            self.pipeline_timestamp = datetime.now(timezone.utc)

        if not product_id:
            product_id = f"SKU-EXP-{abs(hash(product_name)) % 9000 + 1000}"

        now_utc = datetime.now(timezone.utc)
        if expiry_date and not days_remaining:
            try:
                exp_dt = datetime.strptime(expiry_date, "%Y-%m-%d").date()
                days_remaining = (exp_dt - now_utc.date()).days
            except Exception:
                pass
        elif days_remaining is not None and not expiry_date:
            from datetime import timedelta
            exp_dt = now_utc.date() + timedelta(days=days_remaining)
            expiry_date = exp_dt.strftime("%Y-%m-%d")

        # Automatic discount decision rules by Wastage Agent.
        # The tier table (50% <=2d, 30% <=5d, 20% <=7d, 10% <=10d) is shared with the Rio Mart
        # CSV enrichment so a product gets the same discount wherever it is evaluated.
        auto_pct = discount_pct_for_days(days_remaining)
        if days_remaining <= 0:
            decision = "Do Not Sell"
            discount = "100% (Quarantined)"
            reason = f"Expired {abs(days_remaining)} day(s) ago ({expiry_date or 'Past Date'}). Quarantined by Wastage Agent."
        elif auto_pct > 0:
            decision = "Apply Discount"
            discount = discount_override or f"{auto_pct}% Dynamic Promo Discount"
            if days_remaining <= 2:
                reason = f"Critical shelf-life: {days_remaining} day(s) to expiry. {auto_pct}% dynamic markdown applied for fast volume clearance."
            elif days_remaining <= 5:
                reason = f"Expiring in {days_remaining} day(s). {auto_pct}% dynamic promo discount recommended to boost sales velocity."
            elif days_remaining <= 7:
                reason = f"Expiring in {days_remaining} day(s). {auto_pct}% promotional discount applied for inventory turnaround."
            else:
                reason = f"Expiring in {days_remaining} day(s). Early {auto_pct}% discount applied for smooth stock burn."
        else:
            decision = "Sell Normally"
            discount = discount_override or "None"
            reason = f"Healthy shelf-life ({days_remaining} days remaining). Sell at regular price."

        item_entry = {
            "product_id": product_id,
            "product_name": product_name,
            "category": category,
            "expiry_date": expiry_date,
            "days_remaining": days_remaining,
            "decision": decision,
            "discount": discount,
            "reason": reason,
            "unit_cost": unit_cost,
            "current_stock": current_stock,
            "warehouse": warehouse
        }

        # Add to decisions list at the top
        self.wastage_decisions.insert(0, item_entry)
        self._refresh_wastage_summary()

        return {
            "item": item_entry,
            "summary": self.wastage_summary
        }

    @staticmethod
    def _count_wastage(decisions: List[Dict[str, Any]]) -> Dict[str, int]:
        def days_of(d):
            return d.get("days_remaining")
        return {
            "total_products": len(decisions),
            "near_expiry_count": sum(1 for d in decisions if days_of(d) is not None and 0 <= days_of(d) <= NEAR_EXPIRY_MAX_DAYS),
            "discount_count": sum(1 for d in decisions if d.get("decision") == "Apply Discount"),
            "expired_count": sum(1 for d in decisions if d.get("decision") == "Do Not Sell" or (days_of(d) is not None and days_of(d) < 0)),
            "normal_count": sum(1 for d in decisions if d.get("decision") == "Sell Normally"),
        }

    def _refresh_wastage_summary(self):
        """Recalculate wastage KPIs from the decision rows (+ dataset-wide offset, if any)."""
        counts = self._count_wastage(self.wastage_decisions)
        for key, extra in self._wastage_offset.items():
            counts[key] = counts.get(key, 0) + extra
        counts["near_expiry_pct"] = round((counts["near_expiry_count"] / max(counts["total_products"], 1)) * 100, 1)
        merged = {**self.wastage_summary, **counts}
        merged.pop("note", None)  # row-count wording goes stale as soon as an item is added
        merged["displayed_items"] = len(self.wastage_decisions)
        self.wastage_summary = merged

    def load_default_near_expiry_items(self):
        """Populate the initial Wastage Agent view: a few curated near-expiry items plus the Rio Mart near-expiry items."""
        # 1. Curated core perishable items (all still sellable - none are expired)
        default_items = [
            {"product_name": "Amul Taaza Toned Milk 1L", "product_id": "SKU-MILK-101", "category": "Dairy & Refrigerated", "days_remaining": 1, "unit_cost": "₹72", "current_stock": 120},
            {"product_name": "Organic Greek Yogurt 500g", "product_id": "SKU-YOG-204", "category": "Dairy & Refrigerated", "days_remaining": 2, "unit_cost": "₹150", "current_stock": 85},
            {"product_name": "Fresh Strawberries 250g", "product_id": "SKU-STR-308", "category": "Fresh Produce", "days_remaining": 3, "unit_cost": "₹199", "current_stock": 45},
            {"product_name": "Artisanal Sourdough Bread", "product_id": "SKU-BRD-412", "category": "Bakery & Bread", "days_remaining": 4, "unit_cost": "₹110", "current_stock": 35},
            {"product_name": "Fresh Malai Paneer 200g", "product_id": "SKU-PNR-515", "category": "Dairy & Refrigerated", "days_remaining": 5, "unit_cost": "₹95", "current_stock": 90},
            {"product_name": "Free Range Eggs (Pack of 6)", "product_id": "SKU-EGG-618", "category": "Poultry & Meat", "days_remaining": 6, "unit_cost": "₹65", "current_stock": 110},
            {"product_name": "Alphonso Mangoes Premium 1kg", "product_id": "SKU-MNG-721", "category": "Fresh Produce", "days_remaining": 7, "unit_cost": "₹450", "current_stock": 60},
            {"product_name": "Tender Coconut Water 200ml", "product_id": "SKU-BEV-825", "category": "Beverages", "days_remaining": 9, "unit_cost": "₹40", "current_stock": 140},
            {"product_name": "Fresh Pasteurised Cream 250ml", "product_id": "SKU-CRM-930", "category": "Dairy & Refrigerated", "days_remaining": 1, "unit_cost": "₹85", "current_stock": 15},
        ]
        for item in default_items:
            self.add_near_expiry_item(**item)

        # 2. Rio Mart Unified Dataset: stockout + overstock (Inventory Agent) and near-expiry + discounts (Wastage Agent)
        self.load_rio_mart_views()

    def load_rio_mart_views(self):
        """Load the Inventory Agent and Wastage Agent views straight from Rio_Mart_Unified.csv."""
        try:
            from app.services.rio_mart_service import RioMartService

            # Inventory Agent: stockout AND overstock items
            inv = RioMartService.get_inventory_agent_view()
            self.set_inventory_results(inventory_analysis=inv["items"], inventory_summary=inv["summary"])

            # Wastage Agent: near-expiry items, each with a discount (never expired ones)
            wst = RioMartService.get_wastage_agent_view()
            rio_decisions = wst["decisions"]
            sample_counts = self._count_wastage(rio_decisions)
            self._wastage_offset = {
                key: wst["summary"][key] - sample_counts[key]
                for key in sample_counts
                if key in wst["summary"]
            }
            self.wastage_decisions.extend(rio_decisions)
            self.wastage_summary = {
                k: v for k, v in wst["summary"].items()
                if k not in ("note",)
            }
            self.expiry_available = True
            self._refresh_wastage_summary()
        except Exception as err:
            from app.core.logging import logger
            logger.warning(f"Could not load Rio Mart views into pipeline state: {err}")


    def get_full_status(self) -> Dict[str, Any]:
        """Return the full pipeline status for the status endpoint."""
        return {
            "has_run": self.has_run,
            "dataset_id": self.dataset_id,
            "pipeline_timestamp": self.pipeline_timestamp.isoformat() if self.pipeline_timestamp else None,
            "stages": self.stages,
            "available_fields": self.available_fields,
            "missing_field_warnings": self.missing_field_warnings,
            "expiry_available": self.expiry_available,
        }


# Module-level singleton instance
pipeline_state = PipelineState()


