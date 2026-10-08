"""
FastAPI Router for FITQUEST GUIDE™ (In-App Help Assistant)
Provides dedicated API endpoints for platform explanation, onboarding, and navigation.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.guide_service import fitquest_guide_service

router = APIRouter(tags=["FitQuest Guide"])

class GuideChatRequestPayload(BaseModel):
    message: str = Field(..., min_length=1, description="User question or query about FitQuest platform")
    current_view: Optional[str] = Field(None, description="Active view panel ID (e.g. movementDnaView, bodySimView)")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Recent conversation messages")

class GuideChatResponsePayload(BaseModel):
    status: str
    reply: str
    nav_suggestion: Optional[str] = None
    nav_action: Optional[str] = None
    provider: str

@router.post("/guide/chat", response_model=GuideChatResponsePayload, summary="FitQuest Guide™ In-App Help Chatbot")
@router.post("/fitquest-guide/chat", response_model=GuideChatResponsePayload, summary="FitQuest Guide™ In-App Help Chatbot Alias")
def guide_chat(payload: GuideChatRequestPayload):
    """
    Dedicated in-app help chatbot endpoint for FitQuest Guide™.
    Explains platform features, metrics, controls, and assists with navigation.
    Strictly redirects fitness coaching questions to AI Coach.
    """
    result = fitquest_guide_service.process_guide_query(
        message=payload.message,
        current_view=payload.current_view,
        conversation_history=payload.conversation_history
    )
    return {
        "status": "success",
        "reply": result.get("reply", ""),
        "nav_suggestion": result.get("nav_suggestion"),
        "nav_action": result.get("nav_action"),
        "provider": result.get("provider", "FitQuest Guide")
    }
