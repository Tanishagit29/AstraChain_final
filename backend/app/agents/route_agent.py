from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.agents.base_agent import BaseSupplyChainAgent
from app.models.all_models import AgentActivity
from app.services.route_service import RouteOptimizationService
from app.schemas.routes import RouteOptimizationRequest, MultiStopOptimizationRequest


class RouteOptimizationAgent(BaseSupplyChainAgent):
    """
    Autonomous Route Optimization Agent (AG-04).
    Uses Groq LLM tool-calling to evaluate fleet telemetry, run Nearest-Neighbor + 2-Opt Vehicle Routing
    Problem (VRP) algorithms, and compute fuel savings & ETA adjustments.
    """

    def __init__(self):
        system_prompt = (
            "You are AstraChain Route Optimization Agent (AG-04).\n"
            "Your responsibility is to optimize delivery fleet routes, avoid traffic congestion, and maximize fuel economy.\n\n"
            "INSTRUCTIONS:\n"
            "1. Invoke `optimize_single_route` for point-to-point dispatch rerouting.\n"
            "2. Invoke `optimize_multi_stop_vrp` for solving multi-stop Vehicle Routing Problems (VRP) using 2-Opt algorithms.\n"
            "3. Provide exact ETA, route sequence, and fuel savings rationale."
        )
        super().__init__(
            agent_id="AG-04",
            name="Route Optimization Agent",
            role="Traffic Rerouting & Fuel Economy",
            system_prompt=system_prompt,
        )
        self._register_tools()

    def _register_tools(self):
        schema_single = {
            "type": "function",
            "function": {
                "name": "optimize_single_route",
                "description": "Calculate optimal single-destination route, ETA, and fuel savings for a delivery truck.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "truck_id": {"type": "string", "description": "Truck ID (e.g. 'MH-04-JK-4821')"},
                        "destination": {"type": "string", "description": "Destination name"}
                    },
                    "required": ["truck_id", "destination"]
                }
            }
        }
        self.register_tool(schema_single, self._tool_optimize_single_route)

        schema_multi = {
            "type": "function",
            "function": {
                "name": "optimize_multi_stop_vrp",
                "description": "Solve multi-stop Vehicle Routing Problem (VRP) using Nearest-Neighbor + 2-Opt algorithm.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "truck_id": {"type": "string", "description": "Truck ID"},
                        "origin": {"type": "string", "description": "Origin location"},
                        "stops": {"type": "array", "items": {"type": "string"}, "description": "List of stop locations"},
                        "return_to_origin": {"type": "boolean", "description": "Whether truck returns to origin"}
                    },
                    "required": ["truck_id", "origin", "stops"]
                }
            }
        }
        self.register_tool(schema_multi, self._tool_optimize_multi_stop_vrp)

    def _tool_optimize_single_route(self, db: Session, truck_id: str, destination: str) -> Dict[str, Any]:
        req = RouteOptimizationRequest(truck_id=truck_id, destination=destination)
        optimized_route = RouteOptimizationService.optimize_route(db, req)
        return {
            "route_id": optimized_route.id,
            "truck_id": truck_id,
            "destination": destination,
            "eta": optimized_route.eta,
            "fuel_saved": optimized_route.fuelSaved
        }

    def _tool_optimize_multi_stop_vrp(
        self, db: Session, truck_id: str, origin: str, stops: List[str], return_to_origin: bool = False
    ) -> Dict[str, Any]:
        req = MultiStopOptimizationRequest(
            truck_id=truck_id, origin=origin, stops=stops, return_to_origin=return_to_origin
        )
        plan = RouteOptimizationService.optimize_multi_stop(db, req)
        return {
            "truck_id": truck_id,
            "origin": origin,
            "optimized_sequence": plan.optimized_sequence,
            "total_distance_km": plan.total_distance_km,
            "distance_saved_km": plan.distance_saved_km,
            "fuel_saved_inr": plan.fuel_saved_inr
        }

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        db = state.get("db")
        truck_id = state.get("truck_id", "MH-04-JK-4821")
        destination = state.get("destination", "Pune Logistics Hub")
        return self.execute(db, truck_id=truck_id, destination=destination)

    def execute(self, db: Session, truck_id: str = "MH-04-JK-4821", destination: str = "Pune Logistics Hub") -> Dict[str, Any]:
        task = f"Optimize delivery route for truck '{truck_id}' bound for '{destination}'."
        res = self.run(task=task, context={"db": db, "truck_id": truck_id, "destination": destination})

        req = RouteOptimizationRequest(truck_id=truck_id, destination=destination)
        optimized_route = RouteOptimizationService.optimize_route(db, req)

        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        action_msg = f"optimized route for truck '{truck_id}' → '{destination}'."
        details_msg = f"ETA: {optimized_route.eta}. Estimated Fuel Saved: {optimized_route.fuelSaved}."
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
                confidence="98%",
                tasks_processed=1,
                latency="11ms",
                action=action_msg,
                details=details_msg,
                time_ago="Just now",
                color="primary-container"
            )
            db.add(act)
        db.commit()

        res.update({
            "route_id": optimized_route.id,
            "eta": optimized_route.eta,
            "fuel_saved": optimized_route.fuelSaved
        })
        return res

    def execute_multi_stop(
        self,
        db: Session,
        truck_id: str,
        origin: str,
        stops: List[str],
        return_to_origin: bool = False,
    ) -> Dict[str, Any]:
        task = f"Solve {len(stops)}-stop VRP for truck '{truck_id}' starting at '{origin}' visiting {stops}."
        res = self.run(
            task=task,
            context={"db": db, "truck_id": truck_id, "origin": origin, "stops": stops, "return_to_origin": return_to_origin}
        )

        req = MultiStopOptimizationRequest(
            truck_id=truck_id, origin=origin, stops=stops, return_to_origin=return_to_origin
        )
        plan = RouteOptimizationService.optimize_multi_stop(db, req)

        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        summary = (
            f"solved {plan.total_stops}-stop VRP for truck '{truck_id}' via Nearest Neighbor + 2-Opt "
            f"(saved {plan.distance_saved_km} km / ₹{plan.fuel_saved_inr:,.0f})."
        )
        details = f"Optimized sequence: {' → '.join(plan.optimized_sequence)}."
        if act:
            act.tasks_processed += 1
            act.action = summary
            act.details = details
            act.time_ago = "Just now"
        else:
            act = AgentActivity(
                agent_code=self.agent_id,
                agent=self.name,
                role=self.role,
                status="ACTIVE",
                confidence="97%",
                tasks_processed=1,
                latency="18ms",
                action=summary,
                details=details,
                time_ago="Just now",
                color="primary-container"
            )
            db.add(act)
        db.commit()

        res.update({
            "truck_id": truck_id,
            "optimized_sequence": plan.optimized_sequence,
            "total_distance_km": plan.total_distance_km,
            "distance_saved_km": plan.distance_saved_km,
            "fuel_saved_inr": plan.fuel_saved_inr,
        })
        return res

    def fallback_execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        db = context.get("db")
        truck_id = context.get("truck_id", "MH-04-JK-4821")
        destination = context.get("destination", "Pune Logistics Hub")

        if not db:
            return {"status": "FALLBACK", "agent_id": self.agent_id, "route_id": 1, "eta": "14:35", "fuel_saved": "₹1,000"}

        req = RouteOptimizationRequest(truck_id=truck_id, destination=destination)
        optimized_route = RouteOptimizationService.optimize_route(db, req)

        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        if act:
            act.tasks_processed += 1
            act.action = f"optimized route for truck '{truck_id}' → '{destination}'."
            act.time_ago = "Just now"
            db.commit()

        return {
            "status": "FALLBACK",
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "route_id": optimized_route.id,
            "eta": optimized_route.eta,
            "fuel_saved": optimized_route.fuelSaved,
            "tools_executed": [],
            "reasoning_steps": ["Groq API key missing. Executed deterministic Route Optimization Service."]
        }
