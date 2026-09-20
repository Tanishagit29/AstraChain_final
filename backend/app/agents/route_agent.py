from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.agents.base_agent import BaseSupplyChainAgent
from app.models.all_models import AgentActivity
from app.services.route_service import RouteOptimizationService
from app.schemas.routes import RouteOptimizationRequest, MultiStopOptimizationRequest


class RouteOptimizationAgent(BaseSupplyChainAgent):
    def __init__(self):
        super().__init__(
            agent_id="AG-04",
            name="Route Optimization Agent",
            role="Traffic Rerouting & Fuel Economy"
        )

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(state.get("db"), state.get("truck_id", "MH-04-JK-4821"), state.get("destination", "Pune Logistics Hub"))

    def execute(self, db: Session, truck_id: str = "MH-04-JK-4821", destination: str = "Pune Logistics Hub") -> Dict[str, Any]:
        req = RouteOptimizationRequest(truck_id=truck_id, destination=destination)
        optimized_route = RouteOptimizationService.optimize_route(db, req)

        act = db.query(AgentActivity).filter(AgentActivity.agent_code == self.agent_id).first()
        if act:
            act.tasks_processed += 1
            act.action = f"optimized route for truck '{truck_id}' → '{destination}'."
            act.details = f"ETA: {optimized_route.eta}. Estimated Fuel Saved: {optimized_route.fuelSaved}."
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
                action=f"optimized route for truck '{truck_id}' → '{destination}'.",
                details=f"ETA: {optimized_route.eta}. Estimated Fuel Saved: {optimized_route.fuelSaved}.",
                time_ago="Just now",
                color="primary-container"
            )
            db.add(act)
        db.commit()

        return {
            "status": "SUCCESS",
            "agent_id": self.agent_id,
            "route_id": optimized_route.id,
            "eta": optimized_route.eta,
            "fuel_saved": optimized_route.fuelSaved
        }

    def execute_multi_stop(
        self,
        db: Session,
        truck_id: str,
        origin: str,
        stops: List[str],
        return_to_origin: bool = False,
    ) -> Dict[str, Any]:
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

        return {
            "status": "SUCCESS",
            "agent_id": self.agent_id,
            "truck_id": truck_id,
            "optimized_sequence": plan.optimized_sequence,
            "total_distance_km": plan.total_distance_km,
            "distance_saved_km": plan.distance_saved_km,
            "fuel_saved_inr": plan.fuel_saved_inr,
        }
