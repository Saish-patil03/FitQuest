from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.auth import get_current_user_id
from backend.schemas.user import UserCreate, UserResponse
from backend.services.workout_service import workout_service

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("", summary="Create a new User Profile (Deprecated)")
@router.post("/", summary="Create a new User Profile (Deprecated)")
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Direct user creation is disabled. Directs clients to secure registration endpoint.
    """
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Direct user creation is deprecated. Please use POST /api/v1/auth/register with password hashing."
    )

@router.get("", summary="List all Users (Disabled)")
@router.get("/", summary="List all Users (Disabled)")
def list_users():
    """
    Public user enumeration is disabled for privacy and multi-user data isolation.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="User directory listing is disabled for privacy and security."
    )

@router.get("/{user_id}", response_model=UserResponse, summary="Get User Profile by ID")
def get_user(
    user_id: int,
    auth_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Retrieves user profile details by ID.
    Enforces authorization: users can only view their own profile.
    """
    if auth_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Cannot view another user's profile."
        )
    user = workout_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found.")
    return user

