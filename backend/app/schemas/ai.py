from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class AIChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default-session"
    context: Optional[Dict[str, Any]] = None


class AIChatResponse(BaseModel):
    reply: str
    agent_id: str = "AG-06"
    agent_name: str = "Copilot Assistant Agent"
    suggested_actions: Optional[List[str]] = None
    tools_executed: Optional[List[Dict[str, Any]]] = None
    reasoning_steps: Optional[List[str]] = None


class AIRecommendationOut(BaseModel):
    id: str
    type: str
    product: str
    riskText: str
    actionText: str
    actionClass: str

class AIAgentOut(BaseModel):
    id: str
    name: str
    role: str
    status: str
    confidence: str
    tasksProcessed: int
    latency: str
    lastAction: str
