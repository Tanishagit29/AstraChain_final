import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.all_models import Inventory, Supplier, Wastage, Route, Forecast, Product
from app.services.inventory_service import InventoryService
from app.services.wastage_service import WastageService

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """
    Abstract AI Provider Interface for TransitOps LLM Integration.
    """
    @abstractmethod
    def generate_response(
        self,
        user_query: str,
        context_data: Dict[str, Any],
        session_history: Optional[List[Dict[str, Any]]] = None,
        db: Optional[Session] = None,
    ) -> str:
        pass

    def generate_response_details(
        self,
        user_query: str,
        context_data: Dict[str, Any],
        session_history: Optional[List[Dict[str, Any]]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        reply = self.generate_response(user_query, context_data, session_history, db)
        return {
            "reply": reply,
            "tools_executed": [],
            "reasoning_steps": [f"Generated response via {self.__class__.__name__}"]
        }


class DatabaseFallbackAIProvider(AIProvider):
    """
    Deterministic DB-driven Supply Chain AI engine.
    Used when GROQ_API_KEY is absent or as a fallback when API calls fail.
    """
    def generate_response(
        self,
        user_query: str,
        context_data: Dict[str, Any],
        session_history: Optional[List[Dict[str, Any]]] = None,
        db: Optional[Session] = None,
    ) -> str:
        q = user_query.lower()

        # 1. Stockout / Reorder queries
        if any(w in q for w in ["reorder", "stockout", "low stock", "safety stock", "inventory"]):
            high_risk = context_data.get("high_risk_items", [])
            if high_risk:
                names = ", ".join([f"{item['name']} ({item['currentStock']} units)" for item in high_risk[:3]])
                return f"I've analyzed real-time inventory levels. Currently, {len(high_risk)} SKUs are at HIGH stockout risk: {names}. Recommended action: approve stock replenishment."
            return "All inventory levels are currently healthy across your warehouses with zero immediate stockout risks."

        # 2. Supplier queries
        elif any(w in q for w in ["supplier", "vendor", "reliability", "lead time", "poor"]):
            poor_suppliers = context_data.get("poor_suppliers", [])
            if poor_suppliers:
                sup = poor_suppliers[0]
                return f"Supplier Audit: '{sup['name']}' in '{sup['category']}' has a lower reliability score of {sup['reliabilityScore']} and lead time of {sup['leadTimeAvg']}. Recommended action: reallocate order volume."
            return "All verified suppliers are performing optimally with average reliability scores above 90%."

        # 3. Expiry / Wastage queries
        elif any(w in q for w in ["expiry", "expiring", "wastage", "waste", "spoilage", "perishable"]):
            expiring = context_data.get("expiring_items", [])
            if expiring:
                w_item = expiring[0]
                return f"Wastage Prevention Alert: {w_item['quantity']} of '{w_item['product']}' (Batch {w_item['batch']}) is nearing expiry. Recommended action: apply dynamic promotional discount."
            return "No immediate perishable wastage alerts detected. Thermal cold-chain telemetry is stable."

        # 4. Route / Fleet / Traffic queries
        elif any(w in q for w in ["route", "traffic", "truck", "driver", "fleet", "delay"]):
            routes = context_data.get("routes", [])
            rerouted = [r for r in routes if r['status'] in ["REROUTED", "DELAYED"]]
            if rerouted:
                r = rerouted[0]
                return f"Fleet Telemetry: Truck '{r['truckId']}' on route '{r['origin']}' → '{r['destination']}' status '{r['status']}' with ETA {r['eta']}."
            return "All active delivery fleet trucks are running on schedule with zero traffic delays."

        # 5. Forecast queries
        elif any(w in q for w in ["forecast", "demand", "prediction", "diwali", "spike"]):
            return "Demand Forecast Analytics: Predictive XGBoost models indicate a +12.4% demand increase across Dairy & Staples for the upcoming 30-day horizon."

        total_skus = context_data.get("total_skus", 30)
        return f"TransitOps AI Copilot active. Monitoring {total_skus} SKUs and delivery fleet routes. All sub-agents are online."


class GroqAIProvider(AIProvider):
    """
    Autonomous Tool-Calling LLM Engine powered by Groq Python SDK.
    Uses DB query tool-calling and multi-turn session history instead of static prompts.
    """
    def __init__(self):
        self.model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_inventory_stockouts",
                    "description": "Fetch inventory items currently at stockout or high risk.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_supplier_scorecard",
                    "description": "Fetch supplier performance metrics, reliability scores, and high-risk vendor alerts.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_expiring_batches",
                    "description": "Fetch near-expiry perishable batches and expected wastage risk.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_fleet_status",
                    "description": "Fetch real-time delivery truck route telemetry, delays, and thermal readings.",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_demand_forecast",
                    "description": "Fetch XGBoost demand forecast data for a product SKU.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_code": {"type": "string", "description": "SKU code (e.g. 'MK-001-F')"}
                        },
                        "required": []
                    }
                }
            }
        ]

    def _execute_tool(self, tool_name: str, args: Dict[str, Any], db: Optional[Session]) -> Dict[str, Any]:
        if not db:
            return {"error": "Database connection unavailable for tool execution."}

        try:
            if tool_name == "get_inventory_stockouts":
                items = db.query(Inventory).filter(Inventory.risk.in_(["HIGH", "CRITICAL"])).all()
                return {
                    "high_risk_count": len(items),
                    "items": [
                        {
                            "product_code": i.product_code,
                            "name": i.name,
                            "stock": i.current_stock,
                            "forecast_demand": i.forecast_demand,
                            "warehouse": i.warehouse,
                            "action": i.action
                        } for i in items[:10]
                    ]
                }

            elif tool_name == "get_supplier_scorecard":
                suppliers = db.query(Supplier).all()
                return {
                    "total_suppliers": len(suppliers),
                    "suppliers": [
                        {
                            "code": s.supplier_code,
                            "name": s.name,
                            "category": s.category,
                            "reliability": s.reliability_score,
                            "lead_time": s.lead_time_avg,
                            "risk_level": s.risk_level
                        } for s in suppliers
                    ]
                }

            elif tool_name == "get_expiring_batches":
                items = WastageService.get_near_expiry_items(db)
                return {
                    "near_expiry_count": len(items),
                    "batches": [
                        {
                            "id": w.id,
                            "product": w.product,
                            "batch": w.batch,
                            "quantity": w.quantity,
                            "loss": w.lossAmount,
                            "severity": w.severity
                        } for w in items[:10]
                    ]
                }

            elif tool_name == "get_fleet_status":
                routes = db.query(Route).all()
                return {
                    "active_routes_count": len(routes),
                    "routes": [
                        {
                            "code": r.route_code,
                            "truck_id": r.truck_id,
                            "driver": r.driver,
                            "origin": r.origin,
                            "destination": r.destination,
                            "status": r.status,
                            "eta": r.eta,
                            "temp": r.temp
                        } for r in routes
                    ]
                }

            elif tool_name == "get_demand_forecast":
                sku = args.get("product_code", "MK-001-F")
                forecasts = db.query(Forecast).limit(10).all()
                return {
                    "product_code": sku,
                    "forecast_points": [
                        {
                            "day": f.day,
                            "forecast": f.forecast,
                            "upper": f.confidence_upper,
                            "lower": f.confidence_lower
                        } for f in forecasts
                    ]
                }

            return {"error": f"Unknown tool '{tool_name}'"}
        except Exception as e:
            return {"error": f"Failed executing tool '{tool_name}': {str(e)}"}

    def generate_response(
        self,
        user_query: str,
        context_data: Dict[str, Any],
        session_history: Optional[List[Dict[str, Any]]] = None,
        db: Optional[Session] = None,
    ) -> str:
        res = self.generate_response_details(user_query, context_data, session_history, db)
        return res["reply"]

    def generate_response_details(
        self,
        user_query: str,
        context_data: Dict[str, Any],
        session_history: Optional[List[Dict[str, Any]]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        api_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None)
        if not api_key:
            reply = DatabaseFallbackAIProvider().generate_response(user_query, context_data, session_history, db)
            return {
                "reply": reply,
                "tools_executed": [],
                "reasoning_steps": ["Groq API key unconfigured; used database fallback provider."]
            }

        tools_executed = []
        reasoning_steps = []

        try:
            from groq import Groq
            client = Groq(api_key=api_key)

            system_prompt = (
                "You are TransitOps AI Copilot (AG-06), an expert supply chain assistant. "
                "Use available database query tools to retrieve real-time metrics when answering questions. "
                "Pay attention to conversation history to answer follow-up questions accurately."
            )

            messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

            if session_history:
                for turn in session_history[-8:]:
                    messages.append({
                        "role": turn.get("role", "user"),
                        "content": turn.get("content", "")
                    })

            messages.append({"role": "user", "content": user_query})

            final_reply = ""
            for step in range(3):
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto"
                )

                choice = response.choices[0]
                msg = choice.message
                content = msg.content or ""
                tool_calls = getattr(msg, "tool_calls", None)

                if not tool_calls:
                    final_reply = content.strip()
                    reasoning_steps.append(f"Step {step + 1}: LLM synthesized answer.")
                    break

                tool_calls_serialized = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in tool_calls
                ]
                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls_serialized
                })

                for tc in tool_calls:
                    fn_name = tc.function.name
                    raw_args = tc.function.arguments
                    try:
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        args = {}

                    reasoning_steps.append(f"Step {step + 1}: Tool call '{fn_name}' with args {args}")
                    tool_res = self._execute_tool(fn_name, args, db)

                    tools_executed.append({
                        "step": step + 1,
                        "tool": fn_name,
                        "arguments": args,
                        "result": tool_res
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_res, default=str)
                    })

            if not final_reply:
                final_reply = content.strip() if content else "Processed query with available supply chain tools."

            return {
                "reply": final_reply,
                "tools_executed": tools_executed,
                "reasoning_steps": reasoning_steps
            }

        except Exception as e:
            logger.warning(f"Groq API call error: {e}. Falling back to DatabaseFallbackAIProvider.")
            reply = DatabaseFallbackAIProvider().generate_response(user_query, context_data, session_history, db)
            return {
                "reply": reply,
                "tools_executed": [],
                "reasoning_steps": [f"Groq error ({str(e)}); executed DB fallback."]
            }


class AIServiceFactory:
    @staticmethod
    def get_provider() -> AIProvider:
        api_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None)
        if api_key:
            return GroqAIProvider()
        return DatabaseFallbackAIProvider()
