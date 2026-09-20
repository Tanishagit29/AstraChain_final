from typing import Dict, Any
from sqlalchemy.orm import Session
from app.agents.base_agent import BaseSupplyChainAgent
from app.models.all_models import AgentActivity
from app.services.forecast_service import ForecastService
from app.schemas.forecast import GenerateForecastRequest


class ForecastAgent(BaseSupplyChainAgent):
    def __init__(self):
        super().__init__(
            agent_id="AG-01",
            name="Demand & Forecasting Agent",
            role="XGBoost Predictive Analytics & Seasonal Trends"
        )

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(state.get("db"), state.get("product_id"), state.get("horizon_days", 30))

    def execute(self, db: Session, product_id: str = "MK-001-F", horizon_days: int = 30) -> Dict[str, Any]:
        req = GenerateForecastRequest(product_id=product_id, horizon_days=horizon_days)
        forecasts = ForecastService.generate_forecast(db, req)

        # Log activity
        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        if act:
            act.tasks_processed += 1
            act.action = f"generated {horizon_days}-day XGBoost demand forecast for SKU '{product_id}'."
            act.details = f"Processed POS sales & external factors (weather, promo) to project {len(forecasts)} forecast bounds."
            act.time_ago = "Just now"
        else:
            act = AgentActivity(
                agent_code=self.agent_id,
                agent=self.name,
                role=self.role,
                status="ACTIVE",
                confidence="96%",
                tasks_processed=1,
                latency="14ms",
                action=f"generated {horizon_days}-day XGBoost demand forecast for SKU '{product_id}'.",
                details=f"Processed POS sales & external factors (weather, promo) to project {len(forecasts)} forecast bounds.",
                time_ago="Just now",
                color="primary"
            )
            db.add(act)
        db.commit()

        return {
            "status": "SUCCESS",
            "agent_id": self.agent_id,
            "forecast_count": len(forecasts),
            "product_id": product_id
        }
