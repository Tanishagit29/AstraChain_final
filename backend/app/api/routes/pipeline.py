"""
Pipeline API Routes
===================
Serves the latest pipeline results to all frontend pages.
No authentication required — this is a demo/academic project.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.pipeline_state import pipeline_state
from app.services.forecast_service import ForecastService
from app.services.inventory_service import InventoryService
from app.services.wastage_service import WastageService
from app.services.dashboard_service import DashboardService
from app.models.all_models import Inventory, Product, Forecast

router = APIRouter(prefix="/pipeline", tags=["Pipeline Results"])


@router.get("/status")
def get_pipeline_status() -> Dict[str, Any]:
    """Returns the current pipeline execution status."""
    return pipeline_state.get_full_status()


@router.get("/dashboard")
def get_pipeline_dashboard(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns combined dashboard data from actual pipeline results.
    Falls back to DB-driven dashboard if pipeline hasn't run.
    """
    if not pipeline_state.has_run:
        return {
            "has_data": False,
            "message": "No pipeline has been executed yet. Upload a dataset from the Data Ingestion page."
        }


    # Build dashboard from pipeline state
    ds = pipeline_state.dataset_summary
    inv_summary = pipeline_state.inventory_summary
    wst_summary = pipeline_state.wastage_summary

    total_products = ds.get("total_products", 0)
    total_rows = ds.get("total_rows", 0)

    # KPI Metrics from real pipeline data
    kpi_metrics = {
        "totalSales": {
            "value": f"{total_rows} records",
            "delta": f"{total_products} products",
            "status": "positive",
            "timeframe": "from uploaded dataset"
        },
        "inventoryHealth": {
            "value": f"{inv_summary.get('healthy_pct', 0):.0f}%",
            "status": "healthy" if inv_summary.get("healthy_pct", 0) >= 70 else "critical",
            "subtitle": f"{inv_summary.get('available_count', 0)} of {inv_summary.get('total_items', 0)} items optimal"
        },
        "stockoutRisks": {
            "value": str(inv_summary.get("stockout_count", 0)),
            "delta": f"{inv_summary.get('stockout_count', 0)} item(s) at risk",
            "status": "critical" if inv_summary.get("stockout_count", 0) > 0 else "healthy",
            "subtitle": "Predicted demand exceeds stock" if inv_summary.get("stockout_count", 0) > 0 else "All stock levels sufficient"
        },
        "wastageRate": {
            "value": f"{wst_summary.get('near_expiry_count', 0)} items",
            "delta": (f"{wst_summary.get('expired_count', 0)} expired" if wst_summary.get('expired_count', 0) > 0
                      else f"{wst_summary.get('discount_count', 0)} on discount"),
            "status": "critical" if wst_summary.get("expired_count", 0) > 0 else "positive",
            "timeframe": "expiry monitoring active" if pipeline_state.expiry_available else "no expiry data"
        }
    }

    # Demand forecast chart data
    forecast_chart = []
    if pipeline_state.forecast_results:
        forecast_chart = pipeline_state.forecast_results[:14]

    # AI Recommendations from real pipeline analysis
    ai_recommendations = []
    rec_idx = 1

    # Expired items recommendations (Urgent / Critical)
    for decision in pipeline_state.wastage_decisions:
        if decision.get("decision") == "Do Not Sell" and rec_idx <= 3:
            days_ago = abs(decision.get('days_remaining') or 0)
            ai_recommendations.append({
                "id": f"REC-{rec_idx:02d}",
                "type": "EXPIRED",
                "product": decision.get("product_name", "Unknown"),
                "riskText": f"Expired {days_ago} day(s) ago ({decision.get('expiry_date', 'Past Date')})",
                "actionText": "Remove from shelf / Do not sell",
                "actionClass": "bg-error text-on-primary hover:opacity-90"
            })
            rec_idx += 1

    # Stockout risk recommendations
    for item in pipeline_state.inventory_analysis:
        if item.get("status") == "Stockout Risk" and rec_idx <= 4:
            ai_recommendations.append({
                "id": f"REC-{rec_idx:02d}",
                "type": "HIGH_RISK",
                "product": item.get("product_name", "Unknown"),
                "riskText": f"Stockout Risk: {item.get('current_stock', 0)} in stock vs {item.get('predicted_demand', 0)} predicted demand",
                "actionText": f"Reorder {item.get('suggested_reorder_qty') or max(100, item.get('predicted_demand', 0) - item.get('current_stock', 0))} units",
                "actionClass": "bg-error-container text-on-error-container"
            })
            rec_idx += 1

    # Wastage near-expiry recommendations
    for decision in pipeline_state.wastage_decisions:
        if decision.get("decision") == "Apply Discount" and rec_idx <= 6:
            ai_recommendations.append({
                "id": f"REC-{rec_idx:02d}",
                "type": "EXPIRY",
                "product": decision.get("product_name", "Unknown"),
                "riskText": f"Expires in {decision.get('days_remaining', 0)} day(s) ({decision.get('expiry_date', '')})",
                "actionText": f"Apply {decision.get('discount', 'N/A')} promo discount",
                "actionClass": "bg-[#FF9800]/20 text-[#FF9800] hover:bg-[#FF9800]/30"
            })
            rec_idx += 1

    # Overstock recommendations
    for item in pipeline_state.inventory_analysis:
        if item.get("status") == "Overstock" and rec_idx <= 7:
            ai_recommendations.append({
                "id": f"REC-{rec_idx:02d}",
                "type": "OVERSTOCK",
                "product": item.get("product_name", "Unknown"),
                "riskText": f"Overstock: {item.get('current_stock', 0)} units vs {item.get('predicted_demand', 0)} demand",
                "actionText": "Reduce next order by 30%",
                "actionClass": "border border-tertiary text-tertiary hover:bg-tertiary/10"
            })
            rec_idx += 1

    if not ai_recommendations:
        ai_recommendations = [{
            "id": "REC-01",
            "type": "HEALTHY",
            "product": "Supply Chain Network",
            "riskText": "All inventory levels within expected range",
            "actionText": "Pipeline complete — no immediate actions required",
            "actionClass": "bg-primary/10 text-primary"
        }]

    # Automation decisions log
    automation_decisions = []
    for decision in pipeline_state.wastage_decisions[:5]:
        automation_decisions.append({
            "id": decision.get("product_id", ""),
            "agent": "Automation & Wastage Agent",
            "action": f"{decision.get('decision', 'N/A')} for {decision.get('product_name', 'Unknown')}",
            "details": decision.get("reason", ""),
            "time": "Just now",
            "color": "secondary" if decision.get("decision") == "Apply Discount" else "primary"
        })

    for item in pipeline_state.inventory_analysis[:3]:
        automation_decisions.append({
            "id": item.get("product_id", ""),
            "agent": "Inventory Analysis",
            "action": f"{item.get('status', 'N/A')} — {item.get('product_name', 'Unknown')}",
            "details": f"Stock: {item.get('current_stock', 0)} | Demand: {item.get('predicted_demand', 0)}",
            "time": "Just now",
            "color": "tertiary" if item.get("status") == "Stockout Risk" else "primary"
        })

    # Health indicators
    health_indicators = {
        "inventoryEfficiency": f"{inv_summary.get('healthy_pct', 0):.0f}%",
        "dataQuality": f"{ds.get('quality_score', 95)}%",
        "forecastConfidence": f"{pipeline_state.forecast_metric.get('accuracy_pct', 92) if pipeline_state.forecast_metric else 92}%",
        "wastagePrevention": f"{100 - wst_summary.get('near_expiry_pct', 0):.0f}%"
    }

    return {
        "has_data": True,
        "dataset_id": pipeline_state.dataset_id,
        "pipeline_timestamp": pipeline_state.pipeline_timestamp.isoformat() if pipeline_state.pipeline_timestamp else None,
        "kpiMetrics": kpi_metrics,
        "demandForecastData": forecast_chart,
        "aiRecommendations": ai_recommendations,
        "recentActivityLogs": automation_decisions,
        "healthIndicators": health_indicators,
        "stages": pipeline_state.stages,
        "missing_field_warnings": pipeline_state.missing_field_warnings,
    }


@router.get("/forecast")
def get_pipeline_forecast(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns the latest XGBoost forecast results."""
    if not pipeline_state.has_run:
        return {
            "has_data": False,
            "message": "No forecast available. Upload a dataset from the Data Ingestion page."
        }

    return {
        "has_data": True,
        "model": pipeline_state.forecast_model,
        "timestamp": pipeline_state.forecast_timestamp.isoformat() if pipeline_state.forecast_timestamp else None,
        "metric": pipeline_state.forecast_metric,
        "chart_data": pipeline_state.forecast_results,
        "by_product": pipeline_state.forecast_by_product,
        "dataset_id": pipeline_state.dataset_id,
    }


@router.get("/inventory")
def get_pipeline_inventory(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns the latest inventory analysis results."""
    if not pipeline_state.has_run:
        return {
            "has_data": False,
            "message": "No inventory analysis available. Upload a dataset from the Data Ingestion page."
        }

    return {
        "has_data": True,
        "summary": pipeline_state.inventory_summary,
        "items": pipeline_state.inventory_analysis,
        "dataset_id": pipeline_state.dataset_id,
        "missing_warnings": [w for w in pipeline_state.missing_field_warnings if "inventory" in w.lower() or "stock" in w.lower()],
    }


from pydantic import BaseModel
from typing import Dict, Any, Optional

class AddNearExpiryItemRequest(BaseModel):
    product_name: str
    product_id: Optional[str] = None
    category: Optional[str] = "General"
    days_remaining: int = 3
    expiry_date: Optional[str] = None
    discount_override: Optional[str] = None
    unit_cost: Optional[str] = "₹100"
    current_stock: Optional[int] = 100
    warehouse: Optional[str] = "Mumbai Terminal"


@router.get("/wastage")
def get_pipeline_wastage(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns the latest wastage/expiry decisions."""
    if not pipeline_state.has_run:
        return {
            "has_data": False,
            "message": "No wastage analysis available. Upload a dataset from the Data Ingestion page."
        }

    return {
        "has_data": True,
        "expiry_available": pipeline_state.expiry_available,
        "summary": pipeline_state.wastage_summary,
        "decisions": pipeline_state.wastage_decisions,
        "dataset_id": pipeline_state.dataset_id,
    }


@router.post("/wastage/add")
def add_near_expiry_item_endpoint(
    body: AddNearExpiryItemRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Adds a new near-to-expire item with automatic discount calculation to the pipeline state."""
    res = pipeline_state.add_near_expiry_item(
        product_name=body.product_name,
        product_id=body.product_id,
        category=body.category or "General",
        days_remaining=body.days_remaining,
        expiry_date=body.expiry_date,
        discount_override=body.discount_override,
        unit_cost=body.unit_cost or "₹100",
        current_stock=body.current_stock or 100,
        warehouse=body.warehouse or "Mumbai Terminal"
    )
    return {
        "status": "success",
        "message": f"Near-to-expire item '{body.product_name}' added with discount!",
        "data": res["item"],
        "summary": res["summary"]
    }


@router.get("/data-collection")
def get_pipeline_data_collection() -> Dict[str, Any]:
    """Returns the latest data collection and pipeline intelligence results."""
    if not pipeline_state.has_run:
        return {
            "status": "no_data",
            "has_data": False,
            "message": "No dataset uploaded yet."
        }

    return {
        "status": "success",
        "has_data": True,
        "dataset_id": pipeline_state.dataset_id,
        "stages": pipeline_state.stages,
        "dataset_summary": pipeline_state.dataset_summary,
        "quality_report": pipeline_state.quality_report,
        "eda_summary": pipeline_state.eda_summary,
        "preview_columns": pipeline_state.clean_preview_columns,
        "preview_rows": pipeline_state.clean_preview_rows,
        "engineered_columns": pipeline_state.engineered_columns,
        "forecast_summary": {
            "model": "XGBoost",
            "products_forecasted": len(pipeline_state.forecast_by_product),
            "horizon_days": 30,
        },
        "inventory_summary": pipeline_state.inventory_summary,
        "wastage_summary": pipeline_state.wastage_summary,
        "missing_field_warnings": pipeline_state.missing_field_warnings,
    }
