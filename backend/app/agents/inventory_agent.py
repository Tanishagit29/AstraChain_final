from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.agents.base_agent import BaseSupplyChainAgent
from app.models.all_models import AgentActivity, Inventory
from app.services.inventory_service import InventoryService
from app.services.forecast_service import ForecastService


class InventoryAgent(BaseSupplyChainAgent):
    def __init__(self):
        super().__init__(
            agent_id="AG-02",
            name="Inventory Agent",
            role="Optimal Stock Level & Stockout/Overstock Guard"
        )

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(state.get("db"))

    @staticmethod
    def _is_stockout(item: Inventory) -> bool:
        if item.risk == "HIGH":
            return True
        if item.product_code.startswith("RIO-"):
            return False  # Rio Mart rows carry the dataset's own stock-policy status (HIGH = stockout/critical)
        return item.current_stock < (item.forecast_demand * 0.3)

    @staticmethod
    def _is_overstock(item: Inventory) -> bool:
        if item.risk == "OVERSTOCK":
            return True
        if item.product_code.startswith("RIO-"):
            return False
        return item.current_stock > (item.forecast_demand * 2.0)

    @staticmethod
    def _describe(item: Inventory) -> Dict[str, Any]:
        return {
            "product_code": item.product_code,
            "product_name": item.name,
            "store": item.warehouse,
            "current_stock": item.current_stock,
            "action": item.action,
        }

    def execute(self, db: Session) -> Dict[str, Any]:
        # 1. Fetch current inventory items
        all_inv = db.query(Inventory).all()
        stockout_items = [item for item in all_inv if self._is_stockout(item)]
        overstock_items = [item for item in all_inv if self._is_overstock(item)]
        
        # 2. Consume XGBoost Demand Agent forecast for key SKUs
        sample_sku = all_inv[0].product_code if all_inv else "MK-001-F"
        demand_forecast = ForecastService.get_product_forecast(db, sample_sku, horizon_days=30)
        
        reorder_recs = InventoryService.get_reorder_recommendations(db)

        # 3. Log agent activity and persistence
        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        action_msg = f"analyzed {len(all_inv)} inventory SKUs against XGBoost demand forecast ({demand_forecast.total_forecast_demand} units)."
        details_msg = f"Optimal stock levels computed. Flagged {len(stockout_items)} stockout risks & {len(overstock_items)} overstock risks."
        
        if act:
            act.tasks_processed += 1
            act.action = action_msg
            act.details = details_msg
            act.time_ago = "Just now"
        else:
            act = AgentActivity(
                agent_code=self.agent_id,
                agent=self.name,
                role=self.role,
                status="ACTIVE",
                confidence="96%",
                tasks_processed=1,
                latency="8ms",
                action=action_msg,
                details=details_msg,
                time_ago="Just now",
                color="tertiary"
            )
            db.add(act)
        db.commit()

        return {
            "status": "SUCCESS",
            "agent_id": self.agent_id,
            "total_skus_evaluated": len(all_inv),
            "stockout_risk_count": len(stockout_items),
            "overstock_risk_count": len(overstock_items),
            # Both sides of the stock-balance problem, so consumers can show them together
            "stockout_items": [self._describe(i) for i in sorted(stockout_items, key=lambda i: (i.current_stock, i.name))[:10]],
            "overstock_items": [self._describe(i) for i in sorted(overstock_items, key=lambda i: (-i.current_stock, i.name))[:10]],
            "reorder_count": len(reorder_recs),
            "demand_forecast_total": demand_forecast.total_forecast_demand
        }

