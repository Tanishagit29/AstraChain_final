from typing import Dict, Any
from sqlalchemy.orm import Session
from app.agents.base_agent import BaseSupplyChainAgent
from app.models.all_models import AgentActivity
from app.services.wastage_service import WastageService


class WastageAgent(BaseSupplyChainAgent):
    def __init__(self):
        super().__init__(
            agent_id="AG-03",
            name="Automation & Wastage Agent",
            role="Automates Actions & Reduces Wastage via Discount Alerts"
        )

    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(state.get("db"))

    def execute(self, db: Session) -> Dict[str, Any]:
        near_expiry = WastageService.get_near_expiry_items(db)
        discount_alerts = WastageService.get_discount_recommendations(db)
        waste_stats = WastageService.get_expected_waste(db)

        # Automated discount alert summary
        # Near-expiry only (expired products are never discounted or listed), most urgent first.
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

        # Discount range over ALL alerts (the detail list above is capped to the most urgent 50)
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
            "status": "SUCCESS",
            "agent_id": self.agent_id,
            "near_expiry_count": len(near_expiry),
            "discount_alerts_count": len(discount_alerts),
            "discount_alerts": alert_details,
            "discount_pct_min": min(all_pcts) if all_pcts else 0,
            "discount_pct_max": max(all_pcts) if all_pcts else 0,
            "waste_stats": waste_stats
        }

