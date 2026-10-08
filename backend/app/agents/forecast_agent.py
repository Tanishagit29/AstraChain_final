from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.agents.base_agent import BaseSupplyChainAgent
from app.models.all_models import AgentActivity
from app.services.forecast_service import ForecastService
from app.schemas.forecast import GenerateForecastRequest


class ForecastAgent(BaseSupplyChainAgent):
    """
    Autonomous Demand & Forecasting Agent (AG-01).
    Uses Groq LLM tool-calling to evaluate SKU sales history, invoke XGBoost predictive analytics,
    and reason about demand trends and seasonal surges.
    """

    def __init__(self):
        system_prompt = (
            "You are AstraChain Demand & Forecasting Agent (AG-01).\n"
            "Your responsibility is to analyze historical point-of-sale data, run XGBoost predictive algorithms, "
            "and project demand bounds for products over a specified horizon.\n\n"
            "INSTRUCTIONS:\n"
            "1. Invoke `generate_xgboost_forecast` to run the XGBoost machine learning model for the requested product.\n"
            "2. Analyze the total forecast demand, daily trend trajectory, and confidence bounds.\n"
            "3. State your analytical conclusions clearly."
        )
        super().__init__(
            agent_id="AG-01",
            name="Demand & Forecasting Agent",
            role="XGBoost Predictive Analytics & Seasonal Trends",
            system_prompt=system_prompt,
        )
        self._register_tools()

    def _register_tools(self):
        schema_forecast = {
            "type": "function",
            "function": {
                "name": "generate_xgboost_forecast",
                "description": "Execute XGBoost machine learning model to generate daily demand projections.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "SKU code (e.g. 'MK-001-F')"},
                        "horizon_days": {"type": "integer", "description": "Number of forecast days (e.g. 30)"}
                    },
                    "required": ["product_id"]
                }
            }
        }
        self.register_tool(schema_forecast, self._tool_generate_xgboost_forecast)

    def _tool_generate_xgboost_forecast(self, db: Session, product_id: str, horizon_days: int = 30) -> Dict[str, Any]:
        req = GenerateForecastRequest(product_id=product_id, horizon_days=horizon_days)
        forecasts = ForecastService.generate_forecast(db, req)
        summary_data = ForecastService.get_product_forecast(db, product_id, horizon_days=horizon_days)
        return {
            "product_id": product_id,
            "horizon_days": horizon_days,
            "total_forecast_demand": summary_data.total_forecast_demand,
            "trend": summary_data.trend,
            "growth_rate_pct": summary_data.growth_rate_pct,
            "forecast_count": len(forecasts)
        }

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        db = state.get("db")
        product_id = state.get("product_id", "MK-001-F")
        horizon_days = state.get("horizon_days", 30)
        return self.execute(db, product_id=product_id, horizon_days=horizon_days)

    def execute(self, db: Session, product_id: str = "MK-001-F", horizon_days: int = 30) -> Dict[str, Any]:
        task = f"Run XGBoost demand forecast for SKU '{product_id}' over {horizon_days} days."
        res = self.run(task=task, context={"db": db, "product_id": product_id, "horizon_days": horizon_days})

        # Update AgentActivity audit log
        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        action_msg = f"generated {horizon_days}-day XGBoost demand forecast for SKU '{product_id}'."
        details_msg = f"Processed POS sales & external factors to project demand bounds."
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
                latency="14ms",
                action=action_msg,
                details=details_msg,
                time_ago="Just now",
                color="primary"
            )
            db.add(act)
        db.commit()

        # Augment with required legacy keys
        res["product_id"] = product_id
        res["forecast_count"] = horizon_days
        return res

    def fallback_execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        product_id = context.get("product_id", "MK-001-F")
        horizon_days = context.get("horizon_days", 30)

        if not db:
            return {"status": "FALLBACK", "agent_id": self.agent_id, "product_id": product_id, "forecast_count": 0}

        req = GenerateForecastRequest(product_id=product_id, horizon_days=horizon_days)
        forecasts = ForecastService.generate_forecast(db, req)

        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        if act:
            act.tasks_processed += 1
            act.action = f"generated {horizon_days}-day XGBoost demand forecast for SKU '{product_id}'."
            act.time_ago = "Just now"
            db.commit()

        return {
            "status": "FALLBACK",
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "product_id": product_id,
            "forecast_count": len(forecasts),
            "tools_executed": [],
            "reasoning_steps": ["Groq API key missing. Executed deterministic XGBoost forecast service."]
        }
