from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.common import APIResponse
from app.schemas.ai import AIChatRequest, AIChatResponse, AIRecommendationOut, AIAgentOut
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["AI Copilot & Agents"])

@router.post("/chat", response_model=APIResponse[AIChatResponse])
def chat_copilot(req: AIChatRequest, db: Session = Depends(get_db)):
    reply = AIService.process_chat(db, req)
    return APIResponse(
        success=True,
        message="AI copilot query processed successfully.",
        data=reply
    )

@router.get("/recommendations", response_model=APIResponse[List[AIRecommendationOut]])
def get_recommendations(db: Session = Depends(get_db)):
    recs = AIService.get_ai_recommendations(db)
    return APIResponse(
        success=True,
        message="Autonomous AI recommendations retrieved successfully.",
        data=recs
    )

@router.get("/agents", response_model=APIResponse[List[AIAgentOut]])
def get_agents_summary(db: Session = Depends(get_db)):
    agents = AIService.get_ai_agents(db)
    return APIResponse(
        success=True,
        message="AI specialized agents telemetry status retrieved successfully.",
        data=agents
    )
