from typing import Optional
from pydantic import BaseModel

class AutomationRuleOut(BaseModel):
    id: str
    name: str
    trigger: str
    action: str
    status: str
    executionsToday: int

class AutomationActionRequest(BaseModel):
    rule_id: str
    action: str  # "APPROVE", "REJECT", "TOGGLE"
    reason: Optional[str] = None
