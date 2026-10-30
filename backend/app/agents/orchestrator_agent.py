from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.agents.base_agent import BaseSupplyChainAgent
from app.agents.forecast_agent import ForecastAgent
from app.agents.inventory_agent import InventoryAgent
from app.agents.route_agent import RouteOptimizationAgent
from app.agents.wastage_agent import WastageAgent


class OrchestratorAgent(BaseSupplyChainAgent):
    """
    Master Multi-Agent Orchestrator Agent (AG-ORCH).
    Receives natural language supply chain goals and dynamically determines which specialized sub-agents to invoke,
    in what order, and with what specific parameters, skipping non-relevant agents based on LLM reasoning.
    """

    def __init__(self):
        system_prompt = (
            "You are AstraChain Master Supply Chain Orchestrator Agent (AG-ORCH).\n"
            "Your task is to analyze natural language supply-chain goals and dynamically orchestrate execution "
            "by invoking specialized sub-agents as tools.\n\n"
            "AVAILABLE SUB-AGENTS (TOOLS):\n"
            "1. run_forecast_agent(product_id, horizon_days): Invokes Demand & Forecasting Agent (AG-01).\n"
            "2. run_inventory_agent(): Invokes Inventory Agent (AG-02) for safety stock & stockout risks.\n"
            "3. run_route_agent(truck_id, destination): Invokes Route Optimization Agent (AG-04) for VRP routing.\n"
            "4. run_wastage_agent(task_description): Invokes Automation & Wastage Agent (AG-03) for shelf-life & dynamic discounts.\n\n"
            "ORCHESTRATION RULES:\n"
            "- Analyze the user's natural language goal.\n"
            "- Select ONLY the sub-agents relevant to the goal. Skip non-relevant agents.\n"
            "- Execute sub-agents in a logical sequence.\n"
            "- Provide a clear, cohesive final summary explaining the actions taken and results synthesized."
        )
        super().__init__(
            agent_id="AG-ORCH",
            name="Supply Chain Multi-Agent Orchestrator",
            role="Autonomous Task Planner & Multi-Agent Executer",
            system_prompt=system_prompt,
        )
        self._register_tools()

    def _register_tools(self):
        schema_forecast = {
            "type": "function",
            "function": {
                "name": "run_forecast_agent",
                "description": "Run Demand & Forecasting Agent (XGBoost) for a SKU and time horizon.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product SKU (e.g. 'MK-001-F')"},
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
                "description": "Run Inventory Agent to evaluate stockout and overstock risks across warehouses.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        self.register_tool(schema_inventory, self._tool_run_inventory)

        schema_route = {
            "type": "function",
            "function": {
                "name": "run_route_agent",
                "description": "Run Route Optimization Agent for a truck dispatch/reroute to a destination.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "truck_id": {"type": "string", "description": "Truck ID (e.g. 'MH-04-JK-4821')"},
                        "destination": {"type": "string", "description": "Destination hub or warehouse"}
                    },
                    "required": ["destination"]
                }
            }
        }
        self.register_tool(schema_route, self._tool_run_route)

        schema_wastage = {
            "type": "function",
            "function": {
                "name": "run_wastage_agent",
                "description": "Run Automation & Wastage Agent to analyze near-expiry batches and apply dynamic discounts or expedited routing.",
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

    # Tool Implementation Callables wrapping Sub-Agent execute/run

    def _tool_run_forecast(self, db: Session, product_id: str = "MK-001-F", horizon_days: int = 30) -> Dict[str, Any]:
        agent = ForecastAgent()
        return agent.execute(db, product_id=product_id, horizon_days=horizon_days)

    def _tool_run_inventory(self, db: Session) -> Dict[str, Any]:
        agent = InventoryAgent()
        return agent.execute(db)

    def _tool_run_route(self, db: Session, truck_id: str = "MH-04-JK-4821", destination: str = "Pune Logistics Hub") -> Dict[str, Any]:
        agent = RouteOptimizationAgent()
        return agent.execute(db, truck_id=truck_id, destination=destination)

    def _tool_run_wastage(self, db: Session, task_description: str = "Evaluate near-expiry batches") -> Dict[str, Any]:
        agent = WastageAgent()
        return agent.run(task=task_description, context={"db": db})

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        db = state.get("db")
        task = state.get("task", "Analyze supply chain status across all modules.")
        return self.run(task=task, context={"db": db})

    def fallback_execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conditional fallback execution when Groq API key is absent.
        Evaluates keywords in the natural language task to invoke relevant sub-agents.
        """
        db = context.get("db")
        q = task.lower()
        tools_executed = []
        pipeline_results = []

        run_forecast = any(w in q for w in ["forecast", "demand", "diwali", "spike", "prep", "predict"])
        run_inventory = any(w in q for w in ["inventory", "stock", "stockout", "prep", "reorder", "warehouse"])
        run_wastage = any(w in q for w in ["wastage", "waste", "expiry", "perishable", "discount", "urgent", "shelf"])
        run_route = any(w in q for w in ["route", "truck", "transit", "shipment", "reroute", "delay"])

        # If broad task (e.g. "prep warehouse" or "check urgent"), default to standard multi-agent pipeline
        if not (run_forecast or run_inventory or run_wastage or run_route):
            run_forecast = True
            run_inventory = True
            run_wastage = True

        step_count = 0
        if db:
            if run_forecast:
                step_count += 1
                res = self._tool_run_forecast(db)
                tools_executed.append({"step": step_count, "tool": "run_forecast_agent", "result": res})
                pipeline_results.append("Demand & Forecasting Agent executed.")

            if run_inventory:
                step_count += 1
                res = self._tool_run_inventory(db)
                tools_executed.append({"step": step_count, "tool": "run_inventory_agent", "result": res})
                pipeline_results.append("Inventory Agent executed.")

            if run_wastage:
                step_count += 1
                res = self._tool_run_wastage(db, task_description=task)
                tools_executed.append({"step": step_count, "tool": "run_wastage_agent", "result": res})
                pipeline_results.append("Automation & Wastage Agent executed.")

            if run_route:
                step_count += 1
                res = self._tool_run_route(db)
                tools_executed.append({"step": step_count, "tool": "run_route_agent", "result": res})
                pipeline_results.append("Route Optimization Agent executed.")

        summary_text = (
            f"Orchestration completed (Fallback mode: Groq API key unconfigured).\n"
            f"Evaluated task '{task}'. Executed {len(tools_executed)} sub-agent tools: "
            f"{', '.join([t['tool'] for t in tools_executed])}."
        )

        return {
            "status": "FALLBACK",
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "final_content": summary_text,
            "tools_executed": tools_executed,
            "reasoning_steps": pipeline_results,
            "steps": step_count,
        }
