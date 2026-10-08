from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.ai_service import ai_service
from assistant import WorkoutSessionData, UserProfile

router = APIRouter(prefix="/ai", tags=["AI Coaching"])

class AICoachingRequestPayload(BaseModel):
    session_data: WorkoutSessionData
    user_profile: Optional[UserProfile] = None

class FitnessQARequestPayload(BaseModel):
    question: str
    user_profile: Optional[UserProfile] = None

@router.post("/coaching", summary="Generate Standalone AI Workout Coaching Feedback")
def generate_ai_coaching(payload: AICoachingRequestPayload):
    """
    Generates personalized workout coaching insights for a provided WorkoutSessionData payload.
    """
    feedback_text, provider = ai_service.generate_coaching_for_session(
        payload.session_data,
        payload.user_profile
    )
    return {
        "status": "success",
        "exercise_name": payload.session_data.exercise_name,
        "coaching_feedback": feedback_text,
        "provider": provider
    }

@router.post("/qa", summary="General Fitness & Biomechanics Q&A")
def answer_fitness_question(payload: FitnessQARequestPayload):
    """
    Answers user fitness, workout technique, diet, or recovery questions using AI Assistant.
    """
    answer = ai_service.answer_fitness_question(payload.question, payload.user_profile)
    return {
        "status": "success",
        "question": payload.question,
        "answer": answer
    }
