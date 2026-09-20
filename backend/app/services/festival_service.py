"""
Festival-Wise Demand Forecasting Service
=========================================
Layers Indian-festival demand-uplift knowledge on top of the base
(XGBoost / baseline) forecasts produced by ForecastService, without
altering the underlying models. This keeps the core forecasting models
generic and lets the festival calendar be extended independently.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.all_models import Product, Inventory
from app.forecasting import festival_calendar
from app.schemas.forecast import (
    ForecastItem,
    FestivalCalendarItem,
    FestivalImpactItem,
    FestivalForecastResponse,
    FestivalItemDemand,
    FestivalItemDemandResponse,
)
from app.services.forecast_service import ForecastService
from app.services.pipeline_state import pipeline_state


class FestivalForecastService:

    @staticmethod
    def get_calendar(years: Optional[List[int]] = None) -> List[FestivalCalendarItem]:
        entries = festival_calendar.get_calendar(years)
        return [FestivalCalendarItem(**entry) for entry in entries]

    @staticmethod
    def get_upcoming_festivals(category: str, within_days: int = 60) -> List[FestivalImpactItem]:
        entries = festival_calendar.get_upcoming_festivals(datetime.now().date(), category, within_days)
        return [FestivalImpactItem(**entry) for entry in entries]

    @staticmethod
    def get_product_festival_forecast(db: Session, product_id: Optional[str] = None, horizon_days: int = 60) -> FestivalForecastResponse:
        """
        Produces a festival-adjusted demand forecast for a product: takes the
        base model forecast and, for every day that falls in an active
        festival window, scales the predicted quantity by that festival's
        category-specific multiplier (with widened confidence bounds to
        reflect the extra uncertainty around festival demand spikes).
        """
        base = ForecastService.get_product_forecast(db, product_id, horizon_days=horizon_days)

        start_date = datetime.now()
        festival_adjusted: List[ForecastItem] = []
        extra_units = 0

        for idx, item in enumerate(base.daily_forecasts, start=1):
            target_date = (start_date + timedelta(days=idx)).date()
            multiplier = festival_calendar.get_multiplier_for_date(target_date, base.category)

            if multiplier > 1.0:
                adjusted_forecast = int(round(item.forecast * multiplier))
                # Confidence bounds widen further than the point forecast to reflect
                # the extra volatility of festival-driven demand spikes.
                uncertainty_factor = 1.0 + (multiplier - 1.0) * 1.4
                adjusted_upper = int(round(item.confidenceUpper * uncertainty_factor))
                adjusted_lower = max(0, int(round(item.confidenceLower * min(multiplier, 1.15))))
                extra_units += max(0, adjusted_forecast - item.forecast)
            else:
                adjusted_forecast = item.forecast
                adjusted_upper = item.confidenceUpper
                adjusted_lower = item.confidenceLower

            festival_adjusted.append(ForecastItem(
                day=item.day,
                historical=item.historical,
                forecast=adjusted_forecast,
                confidenceUpper=adjusted_upper,
                confidenceLower=adjusted_lower,
            ))

        upcoming = festival_calendar.get_upcoming_festivals(start_date.date(), base.category, within_days=horizon_days)

        return FestivalForecastResponse(
            product_id=base.product_id,
            product_name=base.product_name,
            category=base.category,
            horizon_days=horizon_days,
            baseline_total_demand=base.total_forecast_demand,
            festival_adjusted_total_demand=base.total_forecast_demand + extra_units,
            extra_units_from_festivals=extra_units,
            upcoming_festivals=[FestivalImpactItem(**f) for f in upcoming],
            daily_forecasts=base.daily_forecasts,
            festival_adjusted_forecasts=festival_adjusted,
        )

    @staticmethod
    def get_festival_item_demand(
        db: Session,
        festival_name: Optional[str] = None,
        horizon_days: int = 60,
        limit: int = 20
    ) -> FestivalItemDemandResponse:
        """
        Predicts which items/products will be sold the most during a given festival,
        ranking all items by baseline sales, multiplier, projected festival period sales,
        extra buffer units needed, and stock risk status.
        """
        # 1. Resolve Target Festival
        target_fest = None
        if festival_name:
            target_fest = festival_calendar.get_festival_by_name(festival_name)

        if not target_fest:
            upcoming = festival_calendar.get_upcoming_festivals(datetime.now().date(), "General", 120)
            if upcoming:
                target_fest = festival_calendar.get_festival_by_name(upcoming[0]["festival"])
            else:
                target_fest = festival_calendar.get_festival_by_name("Diwali")

        if not target_fest:
            target_fest = {
                "name": "Diwali",
                "date": f"{datetime.now().year}-11-01",
                "days_away": 45,
                "window_before": 10,
                "window_after": 1,
                "category_multipliers": {"Electronics": 1.9, "Bakery": 2.1, "Clothing": 1.7, "Snacks": 1.8},
            }

        fest_name = target_fest["name"]
        fest_date = target_fest["date"]
        days_away = target_fest["days_away"]
        window_days = target_fest.get("window_before", 5) + target_fest.get("window_after", 1) + 1

        # 2. Gather All Products (From DB + Pipeline State)
        product_items_map = {}

        # DB Products
        db_products = db.query(Product).all()
        db_inventory_map = {}
        inv_rows = db.query(Inventory).all()
        for inv in inv_rows:
            db_inventory_map[inv.product_id] = inv.current_stock

        for p in db_products:
            stock = db_inventory_map.get(p.id, 250)
            product_items_map[p.sku] = {
                "product_id": p.sku,
                "product_name": p.name,
                "category": p.category_name or "General",
                "stock": stock,
            }

        # Pipeline Uploaded Products (if present)
        if pipeline_state.forecast_by_product:
            for sku, p_info in pipeline_state.forecast_by_product.items():
                p_id = p_info.get("product_id", sku)
                product_items_map[p_id] = {
                    "product_id": p_id,
                    "product_name": p_info.get("product_name", f"Product {p_id}"),
                    "category": p_info.get("category", "General"),
                    "stock": p_info.get("current_stock", 300),
                }

        # Fallback sample products if empty
        if not product_items_map:
            sample_prods = [
                {"product_id": "SKU-ELE-01", "product_name": "Smart LED TV 55-inch", "category": "Electronics", "stock": 120},
                {"product_id": "SKU-BAK-02", "product_name": "Premium Sweet Gift Box", "category": "Bakery", "stock": 80},
                {"product_id": "SKU-CLO-03", "product_name": "Festive Silk Ethnic Wear", "category": "Clothing", "stock": 95},
                {"product_id": "SKU-SNA-04", "product_name": "Dry Fruit & Snack Hamper", "category": "Snacks", "stock": 140},
                {"product_id": "SKU-BEV-05", "product_name": "Sparkling Beverage Pack", "category": "Beverages", "stock": 210},
                {"product_id": "SKU-HOU-06", "product_name": "Decorative Brass Diya Set", "category": "Household", "stock": 110},
            ]
            for sp in sample_prods:
                product_items_map[sp["product_id"]] = sp

        # 3. Compute Item-Level Festival Surge Predictions
        item_demands: List[FestivalItemDemand] = []
        category_totals = {}

        # Pre-query inventory forecast demand mapping
        inv_map = {inv.product_id: inv.forecast_demand for inv in db.query(Inventory.product_id, Inventory.forecast_demand).all()}
        db_prod_map = {p.sku: p.id for p in db.query(Product).all()}

        for idx, (p_id, pdata) in enumerate(product_items_map.items()):
            cat = pdata["category"]
            multiplier = festival_calendar.get_category_multiplier_for_festival(fest_name, cat)

            # Get forecast daily demand cleanly without repeated XGBoost fits
            baseline_daily = 85.0
            if pipeline_state.forecast_by_product and p_id in pipeline_state.forecast_by_product:
                total_dem = pipeline_state.forecast_by_product[p_id].get("total_forecast_demand", 2500)
                baseline_daily = total_dem / 30.0
            elif idx < 5:
                try:
                    prod_fc = ForecastService.get_product_forecast(db, p_id, horizon_days=30)
                    baseline_daily = (prod_fc.total_forecast_demand / 30.0) if prod_fc and prod_fc.total_forecast_demand else 85.0
                except Exception:
                    baseline_daily = 85.0
            else:
                db_id = db_prod_map.get(p_id)
                dem = inv_map.get(db_id, 2500) if db_id else 2500
                baseline_daily = (dem / 30.0) if dem else 85.0

            baseline_period = int(round(baseline_daily * window_days))
            festival_period = int(round(baseline_period * multiplier))
            extra_units = max(0, festival_period - baseline_period)
            uplift_pct = round((multiplier - 1.0) * 100, 1)

            stock = pdata.get("stock", 250)
            if stock < festival_period:
                stock_status = "Stockout Risk"
            elif stock < (festival_period + extra_units):
                stock_status = "Reorder Buffer Needed"
            else:
                stock_status = "Sufficient Stock"

            if multiplier >= 1.5:
                surge_level = "HIGH"
            elif multiplier >= 1.25:
                surge_level = "MODERATE"
            else:
                surge_level = "STABLE"

            category_totals[cat] = category_totals.get(cat, 0) + extra_units

            item_demands.append(FestivalItemDemand(
                product_id=pdata["product_id"],
                product_name=pdata["product_name"],
                category=cat,
                baseline_daily_demand=round(baseline_daily, 1),
                festival_multiplier=round(multiplier, 2),
                baseline_period_sales=baseline_period,
                festival_period_sales=festival_period,
                extra_units_needed=extra_units,
                uplift_pct=uplift_pct,
                current_stock=stock,
                stock_status=stock_status,
                surge_level=surge_level,
            ))

        # Rank items by projected festival period sales
        item_demands.sort(key=lambda item: item.festival_period_sales, reverse=True)
        top_items = item_demands[:limit]

        top_category = max(category_totals.items(), key=lambda x: x[1])[0] if category_totals else "Electronics"
        total_surge = sum(item.extra_units_needed for item in item_demands)

        return FestivalItemDemandResponse(
            festival_name=fest_name,
            festival_date=fest_date,
            days_away=days_away,
            window_days=window_days,
            top_category=top_category,
            total_surge_units=total_surge,
            items=top_items,
        )

