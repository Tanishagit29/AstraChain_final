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

@router.get("/history", response_model=APIResponse[List[Any]])
def get_automation_history(db: Session = Depends(get_db)):
    history = AutomationService.get_automation_history(db)
    return APIResponse(
        success=True,
        message="Automation execution history retrieved successfully.",
        data=history
    )
