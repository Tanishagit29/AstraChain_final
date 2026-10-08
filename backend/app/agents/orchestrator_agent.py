import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.agents.base_agent import BaseSupplyChainAgent
from app.agents.data_agent import DataAgent
from app.agents.forecast_agent import ForecastAgent
from app.agents.inventory_agent import InventoryAgent
from app.agents.wastage_agent import WastageAgent
from app.agents.route_agent import RouteOptimizationAgent
from app.models.all_models import AgentActivity

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseSupplyChainAgent):
    """
    Master Multi-Agent Orchestrator Agent (AG-ORCH).
    Receives natural language supply chain goals or pipeline execution triggers,
    and dynamically determines which specialized sub-agents to invoke as tools,
    in what sequence, and with what specific parameters.
    No hardcoded pipeline ordering or keyword matching fallbacks.
    """

    def __init__(self):
        system_prompt = (
            "You are AstraChain Master Supply Chain Orchestrator Agent (AG-ORCH).\n"
            "Your responsibility is to analyze natural language supply chain goals or pipeline ingestion triggers "
            "and dynamically orchestrate multi-agent execution by invoking specialized sub-agents as tools.\n\n"
            "AVAILABLE SPECIALIZED SUB-AGENTS (TOOLS):\n"
            "1. `run_forecast_agent(product_id, horizon_days)`: Invokes Demand & Forecasting Agent (AG-01) for XGBoost demand projections.\n"
            "2. `run_inventory_agent()`: Invokes Inventory Agent (AG-02) for safety stock, stockout risk, and overstock analysis.\n"
            "3. `run_wastage_agent(task_description)`: Invokes Automation & Wastage Agent (AG-03) for near-expiry batch monitoring and dynamic discounts.\n"
            "4. `run_route_agent(truck_id, destination)`: Invokes Route Optimization Agent (AG-04) for VRP routing and fuel savings.\n"
            "5. `run_data_agent(filepath)`: Invokes Data Ingestion & Quality Agent (AG-DATA) for dataset column mapping, quality cleaning, and seeded simulation.\n\n"
            "ORCHESTRATION RULES:\n"
            "- Analyze the task context and determine which sub-agents are needed to satisfy the supply chain objective.\n"
            "- Determine the optimal execution sequence based on logical dependencies (e.g. Forecasting -> Inventory -> Wastage -> Route).\n"
            "- Pass relevant parameters to each tool call.\n"
            "- Formulate a cohesive analytical summary explaining the orchestration decisions made and synthesized outcomes."
        )
        super().__init__(
            agent_id="AG-ORCH",
            name="Supply Chain Multi-Agent Orchestrator",
            role="Autonomous Task Planner & Multi-Agent Executer",
            system_prompt=system_prompt,
        )
        self._register_tools()

    def _register_tools(self):
        schema_data = {
            "type": "function",
            "function": {
                "name": "run_data_agent",
                "description": "Run Data Ingestion Agent to inspect, map, clean, simulate missing fields (seed 42), and bulk insert dataset records.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string", "description": "Absolute path to uploaded dataset file."}
                    },
                    "required": ["filepath"]
                }
            }
        }
        self.register_tool(schema_data, self._tool_run_data)

        schema_forecast = {
            "type": "function",
            "function": {
                "name": "run_forecast_agent",
                "description": "Run Demand & Forecasting Agent (XGBoost) for a product SKU and horizon days.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product SKU code (e.g. 'MK-001-F' or 'all')"},
                        "horizon_days": {"type": "integer", "description": "Forecast horizon in days (default 30)"}
                    },
                    "required": []
                }
            }
        }
        self.register_tool(schema_forecast, self._tool_run_forecast)

        schema_inventory = {
            "type": "function",
            "function": {
                "name": "run_inventory_agent",
                "description": "Run Inventory Agent to evaluate stockout risks, safety stock levels, and overstock items.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        self.register_tool(schema_inventory, self._tool_run_inventory)

        schema_wastage = {
            "type": "function",
            "function": {
                "name": "run_wastage_agent",
                "description": "Run Automation & Wastage Agent to analyze near-expiry batches and apply dynamic promo markdowns.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_description": {"type": "string", "description": "Specific focus for wastage evaluation"}
                    },
                    "required": []
                }
            }
        }
        self.register_tool(schema_wastage, self._tool_run_wastage)

        schema_route = {
            "type": "function",
            "function": {
                "name": "run_route_agent",
                "description": "Run Route Optimization Agent to optimize dispatch routes and VRP multi-stop delivery sequences.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "truck_id": {"type": "string", "description": "Truck ID (e.g. 'MH-04-JK-4821')"},
                        "destination": {"type": "string", "description": "Destination hub or warehouse"}
                    },
                    "required": []
                }
            }
        }
        self.register_tool(schema_route, self._tool_run_route)

    def _tool_run_data(self, db: Session, filepath: str) -> Dict[str, Any]:
        agent = DataAgent()
        return agent.execute(db=db, filepath=filepath)

    def _tool_run_forecast(self, db: Session, product_id: str = "MK-001-F", horizon_days: int = 30) -> Dict[str, Any]:
        agent = ForecastAgent()
        return agent.execute(db=db, product_id=product_id, horizon_days=horizon_days)

    def _tool_run_inventory(self, db: Session) -> Dict[str, Any]:
        agent = InventoryAgent()
        return agent.execute(db=db)

    def _tool_run_wastage(self, db: Session, task_description: str = "Evaluate near-expiry batches") -> Dict[str, Any]:
        agent = WastageAgent()
        return agent.execute(db=db)

    def _tool_run_route(self, db: Session, truck_id: str = "MH-04-JK-4821", destination: str = "Pune Logistics Hub") -> Dict[str, Any]:
        agent = RouteOptimizationAgent()
        return agent.execute(db=db, truck_id=truck_id, destination=destination)

    def execute(self, db: Session, task: str = "Orchestrate complete supply chain intelligence pipeline across all modules.") -> Dict[str, Any]:
        """
        Executes autonomous multi-agent orchestration via ReAct tool calling.
        """
        res = self.run(task=task, context={"db": db})

        # Update AgentActivity audit log
        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        act_msg = f"Orchestrated multi-agent pipeline for task: '{task[:60]}...'"
        details_msg = f"Executed {len(res.get('tools_executed', []))} sub-agents autonomously."
        if act:
            act.tasks_processed += 1
            act.action = act_msg
            act.details = details_msg
            act.time_ago = "Just now"
        else:
            act = AgentActivity(
                agent_code=self.agent_id,
                agent=self.name,
                role=self.role,
                status="ACTIVE",
                confidence="99%",
                tasks_processed=1,
                latency="22ms",
                action=act_msg,
                details=details_msg,
                time_ago="Just now",
                color="primary"
            )
            db.add(act)
        db.commit()

        return res

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        db = state.get("db")
        task = state.get("task", "Analyze supply chain status across all modules.")
        return self.execute(db=db, task=task)
