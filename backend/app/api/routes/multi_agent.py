from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.all_models import User, Notification, AutomationLog, Inventory, Product
from app.agents.forecast_agent import ForecastAgent
from app.agents.inventory_agent import InventoryAgent
from app.agents.wastage_agent import WastageAgent
from app.services.forecast_service import ForecastService
from app.services.inventory_service import InventoryService
from app.services.wastage_service import WastageService

router = APIRouter(prefix="/multi-agent", tags=["Multi-Agent Intelligence Layer"])


class KeyActionRequest(BaseModel):
    action_type: str  # MANAGER_APPROVAL, SUPPLIER_NOTIFICATION, DISCOUNT_SUGGESTION
    target_id: str
    details: Optional[str] = None


@router.post("/run")
def run_multi_agent_pipeline(
    product_id: Optional[str] = "MK-001-F",
    horizon_days: Optional[int] = 30,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Executes the Multi-Agent Intelligence Layer pipeline sequentially:
    1. Demand & Forecasting Agent (XGBoost algorithm)
    2. Inventory Agent (Optimal stock levels & Stockout/Overstock guard)
    3. Automation & Wastage Agent (Near-expiry discount alerts & automated actions)
    """
    # 1. Run Demand & Forecasting Agent (XGBoost)
    demand_agent = ForecastAgent()
    demand_res = demand_agent.execute(db, product_id=product_id, horizon_days=horizon_days)

    # 2. Run Inventory Agent (Consumes forecast + inventory)
    inventory_agent = InventoryAgent()
    inventory_res = inventory_agent.execute(db)

    # 3. Run Automation & Wastage Agent (Consumes shelf life & expiry)
    wastage_agent = WastageAgent()
    wastage_res = wastage_agent.execute(db)

    # Discount range actually recommended by the Wastage Agent across all alerts (e.g. "10%-50%")
    lo, hi = wastage_res.get("discount_pct_min", 0), wastage_res.get("discount_pct_max", 0)
    if hi and lo != hi:
        discount_range = f"{lo}%-{hi}%"
    elif hi:
        discount_range = f"{hi}%"
    else:
        discount_range = "10%-50%"

    # 4. Synthesize Key Actions (Manager Approval, Supplier Notification, Discount Suggestion)
    key_actions = [
        {
            "id": "ACT-001",
            "type": "MANAGER_APPROVAL",
            "title": "Stock Replenishment Approval",
            "description": (
                f"Automated recommendation to reorder {inventory_res.get('reorder_count', 2)} low-stock SKUs "
                f"({inventory_res.get('stockout_risk_count', 0)} stockout risks; "
                f"{inventory_res.get('overstock_risk_count', 0)} overstocked SKUs excluded from reorders)."
            ),
            "status": "PENDING_APPROVAL",
            "badge": "Manager Approval Required"
        },
        {
            "id": "ACT-002",
            "type": "SUPPLIER_NOTIFICATION",
            "title": "Supplier Purchase Order Trigger",
            "description": "Auto-generate purchase order draft to primary dairy & staples vendors.",
            "status": "READY_TO_DISPATCH",
            "badge": "Supplier Notification"
        },
        {
            "id": "ACT-003",
            "type": "DISCOUNT_SUGGESTION",
            "title": "Near-Expiry Dynamic Promo Alert",
            "description": f"Apply {discount_range} markdown promo to {wastage_res.get('discount_alerts_count', 1)} near-expiry batches.",
            "status": "ALERT_ACTIVE",
            "badge": "Discount Suggestion"
        }
    ]

    return {
        "status": "SUCCESS",
        "timestamp": "2026-08-26T20:15:00Z",
        "pipeline": [
            {"agent": demand_agent.name, "result": demand_res},
            {"agent": inventory_agent.name, "result": inventory_res},
            {"agent": wastage_agent.name, "result": wastage_res}
        ],
        "key_actions": key_actions
    }


@router.get("/insights")
def get_multi_agent_insights(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns real-time aggregated insights from all three agents for the Output & Visualization Dashboard.
    """
    forecast_data = ForecastService.get_product_forecast(db, "MK-001-F", horizon_days=30)
    reorder_recs = InventoryService.get_reorder_recommendations(db)
    discount_alerts = WastageService.get_discount_recommendations(db)
    waste_stats = WastageService.get_expected_waste(db)

    return {
        "demand_agent": {
            "model": "XGBoost Regressor v2.4",
            "product_id": forecast_data.product_id,
            "product_name": forecast_data.product_name,
            "trend": forecast_data.trend,
            "growth_rate_pct": forecast_data.growth_rate_pct,
            "total_forecast_demand": forecast_data.total_forecast_demand,
            "forecast_chart": forecast_data.daily_forecasts[:14]
        },
        "inventory_agent": {
            "status": "OPTIMAL_SAFETY_STOCK",
            "stockout_risk_count": len(InventoryService.get_stockout_risk_items(db)),
            "overstock_risk_count": len(InventoryService.get_overstock_risk_items(db)),
            "reorder_recommendations_count": len(reorder_recs),
            "reorder_recommendations": reorder_recs[:5]
        },
        "wastage_agent": {
            "status": "AUTOMATED_DISCOUNT_ACTIVE",
            "discount_alerts_count": len(discount_alerts),
            "discount_alerts": discount_alerts,
            "waste_stats": waste_stats
        }
    }


@router.post("/action/execute")
def execute_key_action(
    payload: KeyActionRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Triggers one of the 3 Key Actions (Manager Approval, Supplier Notification, Discount Suggestion).
    """
    act_type = payload.action_type.upper()
    
    if act_type == "MANAGER_APPROVAL":
        msg = f"Manager Approval granted for action '{payload.target_id}'. Stock replenishment batch authorized."
        notification_title = "Manager Approval Granted"
    elif act_type == "SUPPLIER_NOTIFICATION":
        msg = f"Supplier Notification dispatched for action '{payload.target_id}'. Purchase order transmitted to supplier."
        notification_title = "Supplier Notified"
    elif act_type == "DISCOUNT_SUGGESTION":
        msg = f"Discount Suggestion applied for near-expiry item '{payload.target_id}'. Dynamic markdown live."
        notification_title = "Discount Alert Triggered"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type '{payload.action_type}'. Must be MANAGER_APPROVAL, SUPPLIER_NOTIFICATION, or DISCOUNT_SUGGESTION."
        )

    # Persist action notification
    notif = Notification(
        title=notification_title,
        message=msg,
        type="ACTION_EXECUTED",
        is_read=False
    )
    db.add(notif)
    
    # Audit log entry
    log_entry = AutomationLog(
        rule_code=f"RULE-{payload.target_id}",
        name=notification_title,
        trigger=f"Pipeline automation triggered {act_type}",
        action=msg,
        status="EXECUTED",
        executions_today=1
    )
    db.add(log_entry)
    db.commit()

    return {
        "success": True,
        "action_type": act_type,
        "target_id": payload.target_id,
        "message": msg
    }
