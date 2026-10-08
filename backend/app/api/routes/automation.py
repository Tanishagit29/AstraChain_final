from typing import List, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.automation import AutomationRuleOut, AutomationActionRequest
from app.services.automation_service import AutomationService

router = APIRouter(prefix="/automation", tags=["Automation Center"])

@router.get("/rules", response_model=APIResponse[List[AutomationRuleOut]])
def get_automation_rules(db: Session = Depends(get_db)):
    rules = AutomationService.get_automation_rules(db)
    return APIResponse(
        success=True,
        message="Automation rules retrieved successfully.",
        data=rules
    )

@router.post("/approve", response_model=APIResponse[Any])
def approve_automation_action(req: AutomationActionRequest, db: Session = Depends(get_db)):
    res = AutomationService.approve_action(db, req)
    return APIResponse(
        success=True,
        message="Automation action approved.",
        data=res
    )

@router.post("/reject", response_model=APIResponse[Any])
def reject_automation_action(req: AutomationActionRequest, db: Session = Depends(get_db)):
    res = AutomationService.reject_action(db, req)
    return APIResponse(
        success=True,
        message="Automation action rejected.",
        data=res
    )

from app.services.autonomous_scheduler import autonomous_scheduler

@router.post("/trigger-sweep")
def trigger_autonomous_sweep(db: Session = Depends(get_db)):
    """Triggers an immediate autonomous background agent sweep across inventory, wastage, and festival demand."""
    result = autonomous_scheduler.run_autonomous_sweep(db)
    return APIResponse(
        success=True,
        message="Autonomous background agent sweep executed successfully.",
        data=result
    )

@router.get("/scheduler-status")
def get_scheduler_status():
    """Returns the current status of the background autonomous agent scheduler."""
    return APIResponse(
        success=True,
        message="Scheduler status retrieved.",
        data={
            "is_running": autonomous_scheduler.is_running,
            "interval_seconds": autonomous_scheduler.interval_seconds,
            "last_sweep_time": autonomous_scheduler.last_sweep_time.isoformat() if autonomous_scheduler.last_sweep_time else None,
            "sweeps_completed": autonomous_scheduler.sweeps_completed,
        }
    )

