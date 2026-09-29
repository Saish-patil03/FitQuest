from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.schemas.user import (
    UserRegister,
    UserLogin,
    UserProfileUpdate,
    UserResponse,
    AuthTokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordResponse
)
from backend.services.workout_service import workout_service
from backend.utils.auth import create_access_token, verify_access_token

router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])

def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    """
    Dependency extracting authenticated user ID from Authorization header (Bearer token).
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Please log in."
        )

    token = authorization.replace("Bearer ", "").strip() if authorization.startswith("Bearer ") else authorization.strip()
    user_id = verify_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Please log in again."
        )
    return user_id

@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED, summary="Register a new User Account")
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """
    Registers a new user with email, hashed password, and fitness profile details.
    """
    try:
        user = workout_service.register_user(db, payload)
        token = create_access_token(user.id)
        return AuthTokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Registration failed: {err}")

@router.post("/login", response_model=AuthTokenResponse, summary="User Account Login")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticates user credentials and returns access token + user profile payload.
    """
    user = workout_service.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials."
        )

    token = create_access_token(user.id)
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )

@router.post("/forgot-password", response_model=ForgotPasswordResponse, summary="Request Password Reset Link")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Initiates password reset process for given email.
    Always returns the exact same generic message regardless of whether the email exists to prevent enumeration.
    """
    workout_service.create_password_reset_token(db, payload.email)
    return ForgotPasswordResponse(
        message="If an account exists for this email, password reset instructions have been sent."
    )

@router.post("/reset-password", response_model=ResetPasswordResponse, summary="Reset Account Password via Token")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Resets account password using a valid, non-expired, single-use password reset token.
    """
    try:
        workout_service.reset_password_with_token(db, payload.token, payload.new_password)
        return ResetPasswordResponse(
            message="Your password has been successfully reset. Please log in with your new password."
        )
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Password reset failed: {err}")

@router.get("/me", response_model=UserResponse, summary="Get Current Authenticated User Profile")
def get_me(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """
    Returns authenticated user profile information.
    """
    user = workout_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserResponse.model_validate(user)

@router.post("/logout", summary="User Logout")
def logout():
    """
    Logs out the user (clears session client-side).
    """
    return {"status": "success", "message": "Successfully logged out."}

@router.put("/profile", response_model=UserResponse, summary="Update User Profile Details")
def update_profile(
    payload: UserProfileUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Updates fitness goal, experience level, age, height, weight, gender, or name for current user.
    """
    try:
        user = workout_service.update_user_profile(db, user_id, payload)
        return UserResponse.model_validate(user)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update profile: {err}")

