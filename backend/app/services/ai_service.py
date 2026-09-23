from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.all_models import AgentActivity, Inventory, Supplier, Wastage, Route, Product, ConversationHistory
from app.schemas.ai import AIChatRequest, AIChatResponse, AIRecommendationOut, AIAgentOut
from app.ai.provider import AIServiceFactory


class AIService:
    @staticmethod
    def process_chat(db: Session, req: AIChatRequest) -> AIChatResponse:
        user_msg = req.message
        session_id = req.session_id or "default-session"

        # Load session history turns (last 10 turns)
        past_turns = (
            db.query(ConversationHistory)
            .filter(ConversationHistory.session_id == session_id)
            .order_by(ConversationHistory.timestamp.asc())
            .all()
        )
        history_dicts = [{"role": t.role, "content": t.content} for t in past_turns[-10:]]

        # Gather database context
        high_risk = db.query(Inventory).filter(Inventory.risk == "HIGH").all()
        poor_suppliers = db.query(Supplier).filter(Supplier.risk_level != "LOW").all()
        expiring = db.query(Wastage).filter(Wastage.severity != "LOW").all()
        routes = db.query(Route).all()
        total_skus = db.query(Product).count()

        context_data: Dict[str, Any] = {
            "high_risk_items": [{"name": i.name, "currentStock": i.current_stock, "daysRemaining": i.days_remaining} for i in high_risk],
            "poor_suppliers": [{"name": s.name, "category": s.category, "reliabilityScore": s.reliability_score, "leadTimeAvg": s.lead_time_avg} for s in poor_suppliers],
            "expiring_items": [{"product": w.product, "batch": w.batch, "quantity": w.quantity} for w in expiring],
            "routes": [{"truckId": r.truck_id, "driver": r.driver, "origin": r.origin, "destination": r.destination, "status": r.status, "eta": r.eta, "temp": r.temp} for r in routes],
            "total_skus": total_skus
        }

        # Persist user message to conversation_history
        user_entry = ConversationHistory(session_id=session_id, role="user", content=user_msg)
        db.add(user_entry)
        db.commit()

        # Generate response from AI provider with tool details
        provider = AIServiceFactory.get_provider()
        res_details = provider.generate_response_details(user_msg, context_data, session_history=history_dicts, db=db)
        reply_text = res_details.get("reply", "")

        # Persist assistant response to conversation_history
        assistant_entry = ConversationHistory(session_id=session_id, role="assistant", content=reply_text)
        db.add(assistant_entry)
        db.commit()

        # Dynamic suggested actions based on query intent
        suggested = ["Run demand forecast simulation", "Audit perishable wastage risk"]
        msg_lower = user_msg.lower()
        if "reorder" in msg_lower or "stockout" in msg_lower or "milk" in msg_lower:
            suggested = ["Reorder 500 units Fresh Milk", "View inventory risk details"]
        elif "route" in msg_lower or "truck" in msg_lower:
            suggested = ["View fleet telemetry", "Adjust thermal threshold"]
        elif "supplier" in msg_lower:
            suggested = ["Reallocate order volume", "Review vendor scorecard"]

        return AIChatResponse(
            reply=reply_text,
            agent_id="AG-06",
            agent_name="Copilot Assistant Agent",
            suggested_actions=suggested,
            tools_executed=res_details.get("tools_executed"),
            reasoning_steps=res_details.get("reasoning_steps")
        )

    @staticmethod
    def get_ai_recommendations(db: Session) -> List[AIRecommendationOut]:
        recs = []
        rec_idx = 1

        high_risk_items = db.query(Inventory).filter(Inventory.risk == "HIGH").limit(2).all()
        for h_item in high_risk_items:
            reorder_qty = max(500, h_item.forecast_demand - h_item.current_stock)
            recs.append(
                AIRecommendationOut(
                    id=f"REC-0{rec_idx}",
                    type="HIGH_RISK",
                    product=h_item.name,
                    riskText=f"High stockout risk in {h_item.days_remaining * 24}h ({h_item.warehouse})",
                    actionText=f"Reorder {reorder_qty} units",
                    actionClass="bg-error-container text-on-error-container"
                )
            )
            rec_idx += 1

        overstock_items = db.query(Inventory).filter(Inventory.risk == "OVERSTOCK").limit(1).all()
        for o_item in overstock_items:
            recs.append(
                AIRecommendationOut(
                    id=f"REC-0{rec_idx}",
                    type="OVERSTOCK",
                    product=o_item.name,
                    riskText=f"Overstock: {o_item.current_stock} units holding cost spike",
                    actionText="Reduce next order by 30%",
                    actionClass="border border-tertiary text-tertiary hover:bg-tertiary/10"
                )
            )
            rec_idx += 1

        expiring_items = db.query(Wastage).filter(Wastage.severity != "LOW").limit(1).all()
        for w_item in expiring_items:
            recs.append(
                AIRecommendationOut(
                    id=f"REC-0{rec_idx}",
                    type="EXPIRY",
                    product=w_item.product,
                    riskText=f"Near expiry: {w_item.quantity} in batch {w_item.batch}",
                    actionText="Apply 15% promotional discount",
                    actionClass="bg-[#FF9800]/20 text-[#FF9800] hover:bg-[#FF9800]/30"
                )
            )
            rec_idx += 1

        if not recs:
            recs = [
                AIRecommendationOut(
                    id="REC-01",
                    type="HIGH_RISK",
                    product="Fresh Milk 1L",
                    riskText="High stockout risk in 48h (Mumbai Central)",
                    actionText="Reorder 500 units",
                    actionClass="bg-error-container text-on-error-container"
                )
            ]
        return recs

    @staticmethod
    def get_ai_agents(db: Session) -> List[AIAgentOut]:
        agents = db.query(AgentActivity).all()
        return [
            AIAgentOut(
                id=a.agent_code,
                name=a.agent,
                role=a.role or "Specialized Supply Chain Agent",
                status=a.status,
                confidence=a.confidence,
                tasksProcessed=a.tasks_processed,
                latency=a.latency,
                lastAction=a.action + (" " + a.details if a.details else ""),
            )
            for a in agents
        ]
