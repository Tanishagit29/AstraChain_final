import os
import json
import time
import re
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
    Abstract AI Provider Interface for AstraChain LLM Integration.
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


class GroqAIProvider(AIProvider):
    """
    Autonomous Tool-Calling LLM Engine powered by Groq Python SDK.
    Uses DB query tool-calling and multi-turn session history.
    Strictly checks for GROQ_API_KEY.
    """
    def __init__(self):
        self.model = getattr(settings, "GROQ_MODEL", "openai/gpt-oss-120b")

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
            err_msg = "GROQ_API_KEY is missing or unconfigured in environment. AI Copilot requires a valid GROQ_API_KEY."
            return {
                "reply": err_msg,
                "tools_executed": [],
                "reasoning_steps": [err_msg]
            }

        tools_executed = []
        reasoning_steps = []

        try:
            from groq import Groq
            client = Groq(api_key=api_key)

            system_prompt = (
                "You are AstraChain AI Copilot (AG-06), an expert supply chain assistant. "
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
            for step in range(5):
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
            err_msg = f"GROQ_API_KEY error or API request failed: {str(e)}"
            logger.error(err_msg)
            return {
                "reply": err_msg,
                "tools_executed": tools_executed,
                "reasoning_steps": reasoning_steps + [err_msg]
            }


class AIServiceFactory:
    @staticmethod
    def get_provider() -> AIProvider:
        return GroqAIProvider()
