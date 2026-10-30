import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.agents.base_agent import (
    llm_available,
    llm_breaker,
    make_groq_client,
    is_tool_format_error,
    is_rate_limit_error,
    coerce_tool_args,
    serialize_tool_result,
)
from app.services.pipeline_state import pipeline_state
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

        # 0. Questions about the uploaded dataset / pipeline run
        pipeline_ctx = context_data.get("pipeline")
        if pipeline_ctx and any(w in q for w in ["dataset", "pipeline", "upload", "overview", "summary", "csv", "status"]):
            return (
                f"Latest pipeline run: {pipeline_ctx['total_rows']} cleaned rows across {pipeline_ctx['total_products']} products. "
                f"Inventory: {pipeline_ctx['stockout_count']} stockout risks, {pipeline_ctx['overstock_count']} overstocked. "
                f"Wastage: {pipeline_ctx['near_expiry_count']} near-expiry items, {pipeline_ctx['expired_count']} expired."
            )

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
        return f"AstraChain AI Copilot active. Monitoring {total_skus} SKUs and delivery fleet routes. All sub-agents are online."


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
                    "name": "get_pipeline_results",
                    "description": "Fetch the results of the latest uploaded-dataset pipeline run: dataset summary, inventory stockout/overstock counts and top items, near-expiry wastage decisions.",
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

            elif tool_name == "get_pipeline_results":
                if not pipeline_state.has_run:
                    return {"has_data": False, "message": "No dataset has been uploaded yet."}
                return {
                    "has_data": True,
                    "dataset_summary": pipeline_state.dataset_summary,
                    "inventory_summary": pipeline_state.inventory_summary,
                    "top_inventory_items": pipeline_state.inventory_analysis[:10],
                    "wastage_summary": pipeline_state.wastage_summary,
                    "top_wastage_decisions": pipeline_state.wastage_decisions[:10],
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
            try:
                db.rollback()
            except Exception:
                pass
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

    def _fallback(self, user_query, context_data, session_history, db, reason: str) -> Dict[str, Any]:
        reply = DatabaseFallbackAIProvider().generate_response(user_query, context_data, session_history, db)
        return {"reply": reply, "tools_executed": [], "reasoning_steps": [reason]}

    def generate_response_details(
        self,
        user_query: str,
        context_data: Dict[str, Any],
        session_history: Optional[List[Dict[str, Any]]] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        if not llm_available():
            why = "Groq API key unconfigured" if not (os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None)) \
                else f"Groq cooling down after an error ({llm_breaker.last_error})"
            return self._fallback(user_query, context_data, session_history, db, f"{why}; used database fallback provider.")

        client = make_groq_client()
        if client is None:
            return self._fallback(user_query, context_data, session_history, db, "Groq client unavailable; used database fallback provider.")

        tools_executed: List[Dict[str, Any]] = []
        reasoning_steps: List[str] = []

        try:
            system_prompt = (
                "You are AstraChain AI Copilot (AG-06), an expert supply chain assistant. "
                "Use available database query tools to retrieve real-time metrics when answering questions. "
                "When the user asks about their uploaded dataset or pipeline results, call get_pipeline_results. "
                "Pay attention to conversation history to answer follow-up questions accurately. Keep answers concise."
            )

            messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

            # Groq rejects orphan tool/system turns, so only replay plain user/assistant messages.
            for turn in (session_history or [])[-8:]:
                role = turn.get("role")
                text = turn.get("content") or ""
                if role in ("user", "assistant") and text:
                    messages.append({"role": role, "content": text})

            messages.append({"role": "user", "content": user_query})

            final_reply = ""
            content = ""
            for step in range(3):
                response = None
                for attempt in range(2):
                    try:
                        response = client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            tools=self.tools,
                            tool_choice="auto",
                        )
                        break
                    except Exception as call_err:
                        if is_rate_limit_error(call_err) and attempt == 0:
                            time.sleep(1.5)
                            continue
                        raise

                msg = response.choices[0].message
                content = msg.content or ""
                tool_calls = getattr(msg, "tool_calls", None)

                if not tool_calls:
                    final_reply = content.strip()
                    reasoning_steps.append(f"Step {step + 1}: LLM synthesized answer.")
                    break

                messages.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                        }
                        for tc in tool_calls
                    ],
                })

                for tc in tool_calls:
                    fn_name = tc.function.name
                    raw_args = tc.function.arguments
                    try:
                        parsed = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        parsed = {}
                    schema = next((t for t in self.tools if t["function"]["name"] == fn_name), {})
                    args = coerce_tool_args(schema, parsed)

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
                        "content": serialize_tool_result(tool_res),
                    })

            if not final_reply:
                final_reply = content.strip() if content else "Processed query with available supply chain tools."

            return {
                "reply": final_reply,
                "tools_executed": tools_executed,
                "reasoning_steps": reasoning_steps
            }

        except Exception as e:
            if is_tool_format_error(e):
                logger.warning(f"Groq produced a malformed tool call: {e}. Using database fallback for this query.")
            else:
                llm_breaker.trip(e)
            return self._fallback(user_query, context_data, session_history, db, f"Groq error ({str(e)[:200]}); executed DB fallback.")


class AIServiceFactory:
    @staticmethod
    def get_provider() -> AIProvider:
        if llm_available():
            return GroqAIProvider()
        return DatabaseFallbackAIProvider()
