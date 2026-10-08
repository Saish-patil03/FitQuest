from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    fitness_goal: Optional[str] = "General Fitness"
    experience_level: Optional[str] = "Intermediate"
    password: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[str] = None

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    fitness_goal: Optional[str] = "General Fitness"
    experience_level: Optional[str] = "Beginner"
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    fitness_goal: Optional[str] = None
    experience_level: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    leaderboard_visible: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    fitness_goal: Optional[str] = "General Fitness"
    experience_level: Optional[str] = "Beginner"
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    leaderboard_visible: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ForgotPasswordResponse(BaseModel):
    message: str = "If an account exists for this email, password reset instructions have been sent."

class ResetPasswordResponse(BaseModel):
    message: str = "Your password has been successfully reset. Please log in with your new password."


