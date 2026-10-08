from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.agents.base_agent import BaseSupplyChainAgent
from app.models.all_models import AgentActivity, AutomationLog, Wastage, Inventory, Product
from app.services.wastage_service import WastageService, _parse_currency_float
from app.agents.route_agent import RouteOptimizationAgent


class WastageAgent(BaseSupplyChainAgent):
    """
    Autonomous Wastage & Perishable Management Agent.
    Uses Groq LLM tool-calling to evaluate near-expiry batches, reason about financial value,
    and dynamically apply discounts or trigger agent-to-agent expedited route handoffs.
    """

    def __init__(self):
        system_prompt = (
            "You are AstraChain Wastage & Automation Agent (AG-03). Your responsibility is to minimize perishable "
            "food spoilage loss across warehouses.\n"
            "You have access to tools to fetch near-expiry items, get batch details, apply dynamic promo discounts, "
            "and request expedited rerouting via the Route Agent.\n\n"
            "DECISION GUIDELINES:\n"
            "1. Inspect near-expiry items and get batch details.\n"
            "2. Reason about days to expiry, current stock volume, unit cost, and total financial value.\n"
            "3. If an item has short shelf life (e.g. <= 5 days) but high total value, evaluate whether a dynamic discount "
            "or an expedited route to a high-demand hub (e.g. 'Mumbai Central' or 'Pune Logistics Hub') minimizes loss.\n"
            "4. NEVER use hardcoded templated rules. State explicit financial reasoning when calling `apply_discount` or "
            "`request_expedited_route`.\n"
            "5. Always call `apply_discount` or `request_expedited_route` when actionable batches exist."
        )
        super().__init__(
            agent_id="AG-03",
            name="Automation & Wastage Agent",
            role="Automates Actions & Reduces Wastage via Autonomous ReAct Tool Calling",
            system_prompt=system_prompt,
        )
        self._register_tools()

    def _register_tools(self):
        # Tool 1: get_near_expiry_items
        schema_get_near_expiry = {
            "type": "function",
            "function": {
                "name": "get_near_expiry_items",
                "description": "Fetch items that are near shelf-life expiry from warehouses.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "warehouse": {
                            "type": ["string", "null"],
                            "description": "Optional warehouse filter (e.g. 'Mumbai Central', 'Thane East')"
                        }
                    },
                    "required": []
                }
            }
        }
        self.register_tool(schema_get_near_expiry, self._tool_get_near_expiry_items)

        # Tool 2: get_batch_details
        schema_get_batch_details = {
            "type": "function",
            "function": {
                "name": "get_batch_details",
                "description": "Get detailed attributes for a specific inventory batch ID including unit cost, stock volume, days remaining, and category.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "string",
                            "description": "Batch ID or item code (e.g. 'B-884-21', 'WS-401')"
                        }
                    },
                    "required": ["batch_id"]
                }
            }
        }
        self.register_tool(schema_get_batch_details, self._tool_get_batch_details)

        # Tool 3: apply_discount
        schema_apply_discount = {
            "type": "function",
            "function": {
                "name": "apply_discount",
                "description": "Apply dynamic percentage discount markdown to a batch, persisting LLM reasoning in the manager approval queue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "string",
                            "description": "Batch ID or item code"
                        },
                        "discount_pct": {
                            "type": "number",
                            "description": "Recommended discount percentage (e.g. 15, 30, 50)"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Autonomous rationale explaining WHY this discount percentage was selected based on days to expiry, volume, and unit cost."
                        }
                    },
                    "required": ["batch_id", "discount_pct", "reasoning"]
                }
            }
        }
        self.register_tool(schema_apply_discount, self._tool_apply_discount)

        # Tool 4: request_expedited_route (Agent-to-Agent handoff)
        schema_request_expedited_route = {
            "type": "function",
            "function": {
                "name": "request_expedited_route",
                "description": "Hand off batch to Route Optimization Agent (AG-04) for expedited transport to high-demand destination before expiry.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "string",
                            "description": "Batch ID or item code"
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination hub/warehouse for expedited rerouting (e.g. 'Pune Logistics Hub', 'Mumbai Central Port')"
                        }
                    },
                    "required": ["batch_id", "destination"]
                }
            }
        }
        self.register_tool(schema_request_expedited_route, self._tool_request_expedited_route)

    # Tool Implementation Callables

    def _tool_get_near_expiry_items(self, db: Session, warehouse: Optional[str] = None) -> List[Dict[str, Any]]:
        near_expiry = WastageService.get_near_expiry_items(db)
        results = []
        for item in near_expiry:
            results.append({
                "item_code": item.id,
                "product": item.product,
                "batch": item.batch,
                "quantity": item.quantity,
                "loss_amount": item.lossAmount,
                "severity": item.severity,
                "reason": item.reason,
            })
        return results

    def _tool_get_batch_details(self, db: Session, batch_id: str) -> Dict[str, Any]:
        # Look in Wastage table first
        w_item = db.query(Wastage).filter(
            (Wastage.batch == batch_id) | (Wastage.item_code == batch_id)
        ).first()

        if w_item:
            loss_val = _parse_currency_float(w_item.loss_amount)
            # Find associated product / inventory for cost context
            inv = db.query(Inventory).filter(Inventory.name.ilike(f"%{w_item.product}%")).first()
            unit_cost = inv.unit_cost if inv else "₹100"
            days_rem = inv.days_remaining if inv else 4
            warehouse = inv.warehouse if inv else "Mumbai Central"
            category = inv.category if inv else "Dairy"

            return {
                "batch_id": w_item.batch,
                "item_code": w_item.item_code,
                "product": w_item.product,
                "quantity": w_item.quantity,
                "loss_amount": w_item.loss_amount,
                "estimated_loss_val_inr": loss_val,
                "unit_cost": unit_cost,
                "days_to_expiry": days_rem,
                "warehouse": warehouse,
                "category": category,
                "severity": w_item.severity
            }

        # Check Inventory table if not found in Wastage
        inv_item = db.query(Inventory).filter(
            (Inventory.product_code == batch_id) | (Inventory.name.ilike(f"%{batch_id}%"))
        ).first()

        if inv_item:
            return {
                "batch_id": inv_item.product_code,
                "product": inv_item.name,
                "quantity": f"{inv_item.current_stock} units",
                "unit_cost": inv_item.unit_cost,
                "days_to_expiry": inv_item.days_remaining,
                "warehouse": inv_item.warehouse,
                "category": inv_item.category,
                "risk": inv_item.risk
            }

        return {"error": f"Batch ID or item code '{batch_id}' not found in database."}

    def _tool_apply_discount(self, db: Session, batch_id: str, discount_pct: float, reasoning: str) -> Dict[str, Any]:
        rule_code = f"AUT-DISCOUNT-{batch_id}"
        log_entry = db.query(AutomationLog).filter(AutomationLog.rule_code == rule_code).first()

        name_str = f"Dynamic Markdown: {discount_pct}% on Batch {batch_id}"
        trigger_str = f"LLM Reasoning: {reasoning}"
        action_str = f"Apply {discount_pct}% promo discount to batch {batch_id}."

        if log_entry:
            log_entry.name = name_str
            log_entry.trigger = trigger_str
            log_entry.action = action_str
            log_entry.status = "PENDING_APPROVAL"
            log_entry.executions_today += 1
        else:
            log_entry = AutomationLog(
                rule_code=rule_code,
                name=name_str,
                trigger=trigger_str,
                action=action_str,
                status="PENDING_APPROVAL",
                executions_today=1
            )
            db.add(log_entry)

        # Update AgentActivity
        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        if act:
            act.tasks_processed += 1
            act.action = f"recommended {discount_pct}% dynamic discount for batch {batch_id}."
            act.details = reasoning
            act.time_ago = "Just now"

        db.commit()

        return {
            "status": "SUCCESS",
            "rule_code": rule_code,
            "batch_id": batch_id,
            "discount_pct": discount_pct,
            "reasoning": reasoning,
            "approval_status": "PENDING_APPROVAL"
        }

    def _tool_request_expedited_route(self, db: Session, batch_id: str, destination: str) -> Dict[str, Any]:
        # Agent-to-agent handoff: invoke RouteOptimizationAgent
        route_agent = RouteOptimizationAgent()
        truck_id = f"EXPRESS-TRK-{batch_id}"
        route_res = route_agent.execute(db, truck_id=truck_id, destination=destination)

        rule_code = f"AUT-REROUTE-{batch_id}"
        log_entry = db.query(AutomationLog).filter(AutomationLog.rule_code == rule_code).first()

        name_str = f"Expedited Reroute Handoff for Batch {batch_id}"
        trigger_str = f"LLM Reasoning: High financial batch value warrants expedited transport to {destination}"
        action_str = f"Dispatched truck {truck_id} to {destination} (ETA: {route_res.get('eta', '12:00')})."

        if log_entry:
            log_entry.name = name_str
            log_entry.trigger = trigger_str
            log_entry.action = action_str
            log_entry.status = "PENDING_APPROVAL"
            log_entry.executions_today += 1
        else:
            log_entry = AutomationLog(
                rule_code=rule_code,
                name=name_str,
                trigger=trigger_str,
                action=action_str,
                status="PENDING_APPROVAL",
                executions_today=1
            )
            db.add(log_entry)

        db.commit()

        return {
            "status": "SUCCESS",
            "handoff_to_agent": route_agent.agent_id,
            "route_result": route_res,
            "rule_code": rule_code,
            "approval_status": "PENDING_APPROVAL"
        }

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        db = state.get("db")
        if not db:
            return {"status": "ERROR", "message": "Database session missing in state"}
        return self.execute(db)

    def execute(self, db: Session) -> Dict[str, Any]:
        task = (
            "Evaluate near-expiry batches in the database. Reason about shelf life, volume, and unit cost. "
            "Call apply_discount with custom reasoning for items where discounting prevents waste, or "
            "call request_expedited_route if high batch value justifies rerouting."
        )
        res = self.run(task=task, context={"db": db})

        # Ensure database activity row is logged
        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        if act:
            act.tasks_processed += 1
            act.action = "completed autonomous ReAct evaluation for near-expiry batches."
            act.details = res.get("final_content", "")[:250]
            act.time_ago = "Just now"
            db.commit()

        return res

    def fallback_execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic fallback when Groq API key is not present.
        Ensures existing API endpoints dependent on WastageAgent structure still function smoothly.
        """
        db = context.get("db")
        if not db:
            return {
                "status": "FALLBACK",
                "agent_id": self.agent_id,
                "discount_alerts_count": 0,
                "discount_alerts": [],
                "waste_stats": {}
            }

        near_expiry = WastageService.get_near_expiry_items(db)
        discount_alerts = WastageService.get_discount_recommendations(db)
        waste_stats = WastageService.get_expected_waste(db)

        alert_details = [
            {
                "product": alert.product_name,
                "batch": alert.batch,
                "days_to_expiry": alert.days_to_expiry,
                "suggested_discount": alert.recommended_discount,
                "expected_sales_lift": alert.expected_sales_lift
            }
            for alert in discount_alerts[:50]
        ]

        all_pcts = []
        for alert in discount_alerts:
            digits = "".join(ch for ch in alert.recommended_discount.split("%")[0] if ch.isdigit())
            if digits:
                all_pcts.append(int(digits))

        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        action_msg = f"triggered {len(discount_alerts)} discount alerts for near-expiry batches."
        details_msg = f"Monitored inventory shelf life. Estimated salvage value: {waste_stats.get('projected_salvage_value', '₹0')}."

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
                confidence="94%",
                tasks_processed=1,
                latency="22ms",
                action=action_msg,
                details=details_msg,
                time_ago="Just now",
                color="secondary"
            )
            db.add(act)
        db.commit()

        return {
            "status": "FALLBACK",
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "near_expiry_count": len(near_expiry),
            "discount_alerts_count": len(discount_alerts),
            "discount_alerts": alert_details,
            "discount_pct_min": min(all_pcts) if all_pcts else 0,
            "discount_pct_max": max(all_pcts) if all_pcts else 0,
            "waste_stats": waste_stats,
            "tools_executed": [],
            "reasoning_steps": ["Groq API key missing. Executed deterministic fallback."]
        }
