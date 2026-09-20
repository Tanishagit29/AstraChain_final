from typing import List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.all_models import AutomationLog, Notification
from app.schemas.automation import AutomationRuleOut, AutomationActionRequest


class AutomationService:
    @staticmethod
    def get_automation_rules(db: Session) -> List[AutomationRuleOut]:
        rules = db.query(AutomationLog).all()
        return [
            AutomationRuleOut(
                id=r.rule_code,
                name=r.name,
                trigger=r.trigger,
                action=r.action,
                status=r.status,
                executionsToday=r.executions_today,
            )
            for r in rules
        ]

    @staticmethod
    def approve_action(db: Session, req: AutomationActionRequest) -> dict:
        rule = db.query(AutomationLog).filter(AutomationLog.rule_code == req.rule_id).first()
        if not rule:
            rule = db.query(AutomationLog).first()

        if rule:
            rule.executions_today += 1
            rule.status = "ENABLED"
            db.commit()

            # Create notification
            db.add(Notification(
                title=f"Automation Action Approved: {rule.name}",
                message=f"Action '{rule.action}' approved and executed successfully.",
                type="SUCCESS",
                is_read=False
            ))
            db.commit()

        return {
            "rule_id": req.rule_id,
            "status": "APPROVED",
            "message": f"Action for rule '{req.rule_id}' approved and executed successfully."
        }

    @staticmethod
    def reject_action(db: Session, req: AutomationActionRequest) -> dict:
        rule = db.query(AutomationLog).filter(AutomationLog.rule_code == req.rule_id).first()
        if rule:
            db.add(Notification(
                title=f"Automation Action Rejected: {rule.name}",
                message=f"Action rejected by user. Reason: {req.reason or 'User decision'}",
                type="WARNING",
                is_read=False
            ))
            db.commit()

        return {
            "rule_id": req.rule_id,
            "status": "REJECTED",
            "message": f"Action for rule '{req.rule_id}' rejected. Reason: {req.reason or 'User decision'}"
        }

    @staticmethod
    def get_automation_history(db: Session) -> List[dict]:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        rules = db.query(AutomationLog).all()
        history = []
        for r in rules:
            history.append({
                "timestamp": now_str,
                "rule": r.name,
                "action": r.action,
                "result": "SUCCESS" if r.status == "ENABLED" else "PENDING"
            })
        return history
