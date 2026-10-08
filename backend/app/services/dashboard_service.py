from typing import Dict, Any, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.models.all_models import (
    Product, Inventory, SalesHistory, Forecast,
    Supplier, Route, Wastage, AgentActivity, Notification
)
from app.schemas.dashboard import DashboardSummaryOut


class DashboardService:
    @staticmethod
    def get_dashboard_summary(db: Session) -> DashboardSummaryOut:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        # 1. Total Sales & Growth Calculation
        recent_sales = db.query(func.sum(SalesHistory.revenue)).filter(SalesHistory.timestamp >= thirty_days_ago).scalar() or 0.0
        prev_sales = db.query(func.sum(SalesHistory.revenue)).filter(
            SalesHistory.timestamp >= sixty_days_ago,
            SalesHistory.timestamp < thirty_days_ago
        ).scalar() or 1.0

        growth_pct = ((recent_sales - prev_sales) / max(prev_sales, 1.0)) * 100
        sales_str = f"₹{recent_sales / 1_000_000:.1f}M" if recent_sales >= 1_000_000 else f"₹{recent_sales / 1_000:.1f}K"
        growth_str = f"{'+' if growth_pct >= 0 else ''}{growth_pct:.1f}%"

        # 2. Inventory Health & Stockout Risks
        total_inv_count = db.query(Inventory).count() or 1
        healthy_inv_count = db.query(Inventory).filter(Inventory.risk == "HEALTHY").count()
        stockout_count = db.query(Inventory).filter(Inventory.risk == "HIGH").count()
        overstock_count = db.query(Inventory).filter(Inventory.risk == "OVERSTOCK").count()

        inv_health_pct = round((healthy_inv_count / total_inv_count) * 100, 1)

        # 3. Wastage Rate Calculation
        total_loss = 0.0
        wastage_rows = db.query(Wastage).all()
        for w in wastage_rows:
            try:
                val = float(w.loss_amount.replace('₹', '').replace(',', '').strip())
                total_loss += val
            except Exception:
                pass
        
        wastage_rate_pct = round((total_loss / max(recent_sales, 1.0)) * 100, 1)

        kpi_metrics = {
            "totalSales": {
                "value": sales_str,
                "delta": growth_str,
                "status": "positive" if growth_pct >= 0 else "negative",
                "timeframe": "vs last month"
            },
            "inventoryHealth": {
                "value": f"{inv_health_pct}%",
                "status": "healthy" if inv_health_pct >= 75 else "critical",
                "subtitle": f"{healthy_inv_count} of {total_inv_count} optimal items"
            },
            "stockoutRisks": {
                "value": str(stockout_count),
                "delta": f"{stockout_count} item(s) high risk",
                "status": "critical" if stockout_count > 0 else "healthy",
                "subtitle": "Immediate reorder required" if stockout_count > 0 else "All stock levels optimal"
            },
            "wastageRate": {
                "value": f"{wastage_rate_pct}%",
                "delta": f"₹{total_loss:,.0f} lost",
                "status": "positive" if wastage_rate_pct < 5.0 else "critical",
                "timeframe": "vs target 4.5%"
            }
        }

        # 4. Demand Forecast Chart Data
        forecast_rows = db.query(Forecast).limit(13).all()
        demand_forecast = [
            {
                "day": f.day,
                "historical": f.historical,
                "forecast": f.forecast,
                "confidenceUpper": f.confidence_upper,
                "confidenceLower": f.confidence_lower,
            }
            for f in forecast_rows
        ]

        # 5. Dynamic AI Recommendations from DB
        ai_recommendations: List[Dict[str, Any]] = []
        rec_idx = 1

        # High Risk Reorder
        high_risk_items = db.query(Inventory).filter(Inventory.risk == "HIGH").limit(2).all()
        for h_item in high_risk_items:
            reorder_qty = max(500, h_item.forecast_demand - h_item.current_stock)
            ai_recommendations.append({
                "id": f"REC-0{rec_idx}",
                "type": "HIGH_RISK",
                "product": h_item.name,
                "riskText": f"High stockout risk ({h_item.days_remaining}d remaining in {h_item.warehouse})",
                "actionText": f"Reorder {reorder_qty} units",
                "actionClass": "bg-error-container text-on-error-container"
            })
            rec_idx += 1

        # Overstock Recommendation
        overstock_items = db.query(Inventory).filter(Inventory.risk == "OVERSTOCK").limit(1).all()
        for o_item in overstock_items:
            ai_recommendations.append({
                "id": f"REC-0{rec_idx}",
                "type": "OVERSTOCK",
                "product": o_item.name,
                "riskText": f"Overstock: {o_item.current_stock} units holding cost spike",
                "actionText": "Reduce next order by 30%",
                "actionClass": "border border-tertiary text-tertiary hover:bg-tertiary/10"
            })
            rec_idx += 1

        # Expiry Recommendation
        expiring_items = db.query(Wastage).filter(Wastage.severity != "LOW").limit(1).all()
        for w_item in expiring_items:
            ai_recommendations.append({
                "id": f"REC-0{rec_idx}",
                "type": "EXPIRY",
                "product": w_item.product,
                "riskText": f"Near expiry: {w_item.quantity} in batch {w_item.batch}",
                "actionText": "Apply 15% promotional discount",
                "actionClass": "bg-[#FF9800]/20 text-[#FF9800] hover:bg-[#FF9800]/30"
            })
            rec_idx += 1

        # Fallback recommendations if empty
        if not ai_recommendations:
            ai_recommendations = [
                {
                    "id": "REC-01",
                    "type": "HEALTHY",
                    "product": "Supply Chain Network",
                    "riskText": "All inventory levels optimal across 5 warehouses",
                    "actionText": "Maintain current reorder schedules",
                    "actionClass": "bg-primary/10 text-primary"
                }
            ]

        # 6. Recent Activity Logs
        activity_rows = db.query(AgentActivity).order_by(AgentActivity.id.desc()).limit(10).all()
        activity_logs = [
            {
                "id": act.agent_code,
                "agent": act.agent,
                "action": act.action,
                "details": act.details,
                "time": act.time_ago,
                "color": act.color,
            }
            for act in activity_rows
        ]

        # 7. Health Indicators Calculation
        suppliers = db.query(Supplier).all()
        rel_scores = []
        for s in suppliers:
            try:
                rel_scores.append(float(s.reliability_score.replace('%', '')))
            except Exception:
                pass
        avg_supplier_rel = int(sum(rel_scores) / len(rel_scores)) if rel_scores else 91

        routes = db.query(Route).all()
        optimal_routes = [r for r in routes if r.status in ["IN_TRANSIT", "OPTIMAL", "REROUTED"]]
        route_opt_pct = int((len(optimal_routes) / len(routes)) * 100) if routes else 87

        health_indicators = {
            "inventoryEfficiency": f"{inv_health_pct:.0f}%",
            "supplierReliability": f"{avg_supplier_rel}%",
            "routeOptimization": f"{route_opt_pct}%",
            "wastagePrevention": f"{max(80, 100 - int(wastage_rate_pct * 2))}%"
        }

        return DashboardSummaryOut(
            kpiMetrics=kpi_metrics,
            demandForecastData=demand_forecast,
            aiRecommendations=ai_recommendations,
            recentActivityLogs=activity_logs,
            healthIndicators=health_indicators
        )
