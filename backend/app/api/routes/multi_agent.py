import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.session import get_db
from app.models.all_models import User, Notification, AutomationLog, Inventory, Product, AgentMessageBoard, DecisionMemory
from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.forecast_agent import ForecastAgent
from app.agents.inventory_agent import InventoryAgent
from app.agents.wastage_agent import WastageAgent
from app.core.config import settings
from app.services.forecast_service import ForecastService
from app.services.inventory_service import InventoryService
from app.services.wastage_service import WastageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/multi-agent", tags=["Multi-Agent Intelligence Layer"])


class KeyActionRequest(BaseModel):
    action_type: str  # MANAGER_APPROVAL, SUPPLIER_NOTIFICATION, DISCOUNT_SUGGESTION, REORDER, DISCOUNT, REROUTE
    target_id: str
    details: Optional[str] = None
    quantity: Optional[int] = None
    discount_pct: Optional[float] = None
    cost_inr: Optional[float] = None



class OrchestrateTaskRequest(BaseModel):
    task: str


class PostAgentMessageRequest(BaseModel):
    sender_agent_id: str
    sender_agent_name: str
    target_agent_id: Optional[str] = None
    subject: str
    content: str
    importance: Optional[str] = "INFO"


class DecisionMemoryRequest(BaseModel):
    agent_id: str
    context_key: str
    decision: str
    rationale: str
    user_feedback: Optional[str] = None



@router.post("/orchestrate")
def orchestrate_multi_agent_task(
    payload: OrchestrateTaskRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Autonomous Multi-Agent Orchestration endpoint (AG-ORCH).
    Given a natural language task, the OrchestratorAgent dynamically determines
    which sub-agents to invoke as tools, in what order, and with what parameters.
    No hardcoded fallbacks or keyword rules.
    """
    api_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": "GROQ_API_KEY is missing or unconfigured in environment. Multi-agent orchestration requires a valid GROQ_API_KEY."
            }
        )

    orchestrator = OrchestratorAgent()
    result = orchestrator.execute(db=db, task=payload.task)

    if result.get("status") == "ERROR":
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": result.get("error"),
                "reasoning_steps": result.get("reasoning_steps", [])
            }
        )

    return {
        "status": "SUCCESS",
        "task": payload.task,
        "summary": result.get("final_content"),
        "tools_executed": result.get("tools_executed"),
        "reasoning_steps": result.get("reasoning_steps"),
        "steps_taken": result.get("steps"),
    }


@router.post("/run")
def run_multi_agent_pipeline(
    product_id: Optional[str] = "MK-001-F",
    horizon_days: Optional[int] = 30,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Executes the Multi-Agent Intelligence Layer pipeline using OrchestratorAgent.
    """
    api_key = os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": "GROQ_API_KEY is missing or unconfigured in environment. Multi-agent pipeline execution requires a valid GROQ_API_KEY."
            }
        )

    task_desc = f"Run complete multi-agent supply chain evaluation for product SKU '{product_id}' over a {horizon_days}-day horizon."
    orchestrator = OrchestratorAgent()
    result = orchestrator.execute(db=db, task=task_desc)

    if result.get("status") == "ERROR":
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": result.get("error"),
                "reasoning_steps": result.get("reasoning_steps", [])
            }
        )

    return result


@router.get("/insights")
def get_multi_agent_insights(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns real-time aggregated insights from all agents for the Dashboard.
    """
    forecast_data = ForecastService.get_product_forecast(db, "MK-001-F", horizon_days=30)
    reorder_recs = InventoryService.get_reorder_recommendations(db)
    discount_alerts = WastageService.get_discount_recommendations(db)
    waste_stats = WastageService.get_expected_waste(db)

    return {
        "demand_agent": {
            "model": "XGBoost Regressor v2.4",
            "product_id": forecast_data.product_id,
            "product_name": forecast_data.product_name,
            "trend": forecast_data.trend,
            "growth_rate_pct": forecast_data.growth_rate_pct,
            "total_forecast_demand": forecast_data.total_forecast_demand,
            "forecast_chart": forecast_data.daily_forecasts[:14]
        },
        "inventory_agent": {
            "status": "OPTIMAL_SAFETY_STOCK",
            "stockout_risk_count": len(InventoryService.get_stockout_risk_items(db)),
            "overstock_risk_count": len(InventoryService.get_overstock_risk_items(db)),
            "reorder_recommendations_count": len(reorder_recs),
            "reorder_recommendations": reorder_recs[:5]
        },
        "wastage_agent": {
            "status": "AUTOMATED_DISCOUNT_ACTIVE",
            "discount_alerts_count": len(discount_alerts),
            "discount_alerts": discount_alerts,
            "waste_stats": waste_stats
        }
    }


@router.get("/pending-approvals")
def get_pending_approvals(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns all high-impact actions waiting for user/manager approval."""
    pending_logs = db.query(AutomationLog).filter(AutomationLog.status == "PENDING_APPROVAL").all()
    return {
        "status": "success",
        "pending_count": len(pending_logs),
        "pending_actions": [
            {
                "id": log.id,
                "rule_code": log.rule_code,
                "name": log.name,
                "trigger": log.trigger,
                "action": log.action,
                "status": log.status,
            }
            for log in pending_logs
        ]
    }


@router.post("/action/evaluate")
def evaluate_action(
    payload: KeyActionRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Evaluates an action proposal.
    Low-risk actions (reorder <=500, discount <=30%, reroute cost <=20k) auto-execute.
    High-impact actions require manager approval and are stored with status PENDING_APPROVAL.
    """
    act_type = payload.action_type.upper()
    is_high_impact = False
    reason = "Routine operational action — auto-executed."

    if act_type == "REORDER" and (payload.quantity or 0) > 500:
        is_high_impact = True
        reason = f"Reorder quantity ({payload.quantity} units) exceeds auto-approval threshold of 500 units."
    elif act_type == "DISCOUNT" and (payload.discount_pct or 0) > 30.0:
        is_high_impact = True
        reason = f"Discount rate ({payload.discount_pct}%) exceeds auto-approval threshold of 30%."
    elif act_type == "REROUTE" and (payload.cost_inr or 0) > 20000.0:
        is_high_impact = True
        reason = f"Rerouting cost (₹{payload.cost_inr:,.0f}) exceeds threshold of ₹20,000."

    rule_code = f"AUT-{payload.target_id}"
    log_entry = db.query(AutomationLog).filter(AutomationLog.rule_code == rule_code).first()

    if is_high_impact:
        if not log_entry:
            log_entry = AutomationLog(
                rule_code=rule_code,
                name=f"High-Impact Action Approval ({act_type})",
                trigger=reason,
                action=f"Pending Approval: {payload.details or act_type} for '{payload.target_id}'",
                status="PENDING_APPROVAL",
                executions_today=0
            )
            db.add(log_entry)
        else:
            log_entry.status = "PENDING_APPROVAL"
            log_entry.action = f"Pending Approval: {payload.details or act_type} for '{payload.target_id}'"

        notif = Notification(
            title=f"Approval Required: {act_type}",
            message=reason,
            type="APPROVAL_REQUIRED",
            is_read=False
        )
        db.add(notif)
        db.commit()

        return {
            "status": "PENDING_APPROVAL",
            "requires_approval": True,
            "reason": reason,
            "target_id": payload.target_id,
            "rule_code": rule_code
        }
    else:
        if not log_entry:
            log_entry = AutomationLog(
                rule_code=rule_code,
                name=f"Auto-Executed Action ({act_type})",
                trigger=reason,
                action=f"Auto-Executed: {payload.details or act_type} for '{payload.target_id}'",
                status="EXECUTED",
                executions_today=1
            )
            db.add(log_entry)
        else:
            log_entry.status = "EXECUTED"
            log_entry.executions_today += 1

        notif = Notification(
            title=f"Action Executed: {act_type}",
            message=f"{payload.details or act_type} for '{payload.target_id}' completed automatically.",
            type="ACTION_EXECUTED",
            is_read=False
        )
        db.add(notif)
        db.commit()

        return {
            "status": "EXECUTED",
            "requires_approval": False,
            "reason": reason,
            "target_id": payload.target_id,
            "rule_code": rule_code
        }


@router.post("/action/execute")
def execute_key_action(
    payload: KeyActionRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Triggers key actions (Manager Approval, Supplier Notification, Discount Suggestion, or approves PENDING_APPROVAL tasks).
    """
    act_type = payload.action_type.upper()

    # Check if there is a pending approval log entry for this target_id or rule_code
    rule_code = f"AUT-{payload.target_id}"
    log_entry = db.query(AutomationLog).filter(
        (AutomationLog.rule_code == rule_code) | (AutomationLog.rule_code == payload.target_id)
    ).first()

    if log_entry and log_entry.status == "PENDING_APPROVAL":
        log_entry.status = "EXECUTED"
        log_entry.executions_today += 1
        msg = f"Manager Approval granted and high-impact action executed for '{payload.target_id}'."
        notification_title = "Action Approved & Executed"
    elif act_type == "MANAGER_APPROVAL":
        msg = f"Manager Approval granted for action '{payload.target_id}'. Stock replenishment batch authorized."
        notification_title = "Manager Approval Granted"
    elif act_type == "SUPPLIER_NOTIFICATION":
        msg = f"Supplier Notification dispatched for action '{payload.target_id}'. Purchase order transmitted to supplier."
        notification_title = "Supplier Notified"
    elif act_type == "DISCOUNT_SUGGESTION":
        msg = f"Discount Suggestion applied for near-expiry item '{payload.target_id}'. Dynamic markdown live."
        notification_title = "Discount Alert Triggered"
    elif act_type in ("REORDER", "DISCOUNT", "REROUTE"):
        msg = f"Action '{act_type}' executed for '{payload.target_id}'."
        notification_title = f"{act_type} Action Executed"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action_type '{payload.action_type}'."
        )

    # Persist action notification
    notif = Notification(
        title=notification_title,
        message=msg,
        type="ACTION_EXECUTED",
        is_read=False
    )
    db.add(notif)

    if not log_entry:
        log_entry = AutomationLog(
            rule_code=rule_code,
            name=notification_title,
            trigger=f"Pipeline automation triggered {act_type}",
            action=msg,
            status="EXECUTED",
            executions_today=1
        )
        db.add(log_entry)

    db.commit()

    return {
        "success": True,
        "action_type": act_type,
        "target_id": payload.target_id,
        "status": "EXECUTED",
        "message": msg
    }


@router.get("/messages")
def get_agent_messages(
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Returns messages from the inter-agent message board (Stage 6)."""
    query = db.query(AgentMessageBoard)
    if agent_id:
        query = query.filter(
            (AgentMessageBoard.sender_agent_id == agent_id) |
            (AgentMessageBoard.target_agent_id == agent_id) |
            (AgentMessageBoard.target_agent_id.is_(None))
        )
    messages = query.order_by(AgentMessageBoard.id.desc()).limit(50).all()
    return {
        "status": "success",
        "count": len(messages),
        "messages": [
            {
                "id": m.id,
                "sender_agent_id": m.sender_agent_id,
                "sender_agent_name": m.sender_agent_name,
                "target_agent_id": m.target_agent_id,
                "subject": m.subject,
                "content": m.content,
                "importance": m.importance,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in messages
        ]
    }


@router.post("/messages")
def post_agent_message(
    payload: PostAgentMessageRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Posts a new message to the inter-agent message board (Stage 6)."""
    msg = AgentMessageBoard(
        sender_agent_id=payload.sender_agent_id,
        sender_agent_name=payload.sender_agent_name,
        target_agent_id=payload.target_agent_id,
        subject=payload.subject,
        content=payload.content,
        importance=payload.importance or "INFO"
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {
        "status": "success",
        "message_id": msg.id,
        "message": f"Message '{payload.subject}' posted by {payload.sender_agent_name}."
    }


@router.get("/decisions")
def get_decision_memories(
    agent_id: Optional[str] = None,
    context_key: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Returns decision memory entries stored by agents (Stage 6)."""
    query = db.query(DecisionMemory)
    if agent_id:
        query = query.filter(DecisionMemory.agent_id == agent_id)
    if context_key:
        query = query.filter(DecisionMemory.context_key == context_key)
    memories = query.order_by(DecisionMemory.id.desc()).limit(50).all()
    return {
        "status": "success",
        "count": len(memories),
        "decisions": [
            {
                "id": d.id,
                "agent_id": d.agent_id,
                "context_key": d.context_key,
                "decision": d.decision,
                "rationale": d.rationale,
                "user_feedback": d.user_feedback,
                "timestamp": d.timestamp.isoformat() if d.timestamp else None,
            }
            for d in memories
        ]
    }


@router.post("/decisions")
def store_decision_memory(
    payload: DecisionMemoryRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Stores a new agent decision and rationale into persistent decision memory (Stage 6)."""
    mem = DecisionMemory(
        agent_id=payload.agent_id,
        context_key=payload.context_key,
        decision=payload.decision,
        rationale=payload.rationale,
        user_feedback=payload.user_feedback
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return {
        "status": "success",
        "memory_id": mem.id,
        "message": f"Decision memory recorded for agent {payload.agent_id}."
    }


