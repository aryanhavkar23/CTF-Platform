from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


class UserRegisterRequest(BaseModel):
    """Schema for new user registration. Role is strictly excluded to prevent privilege escalation."""
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Alphanumeric username with underscores and hyphens"
    )
    email: EmailStr = Field(description="Valid email address")
    password: str = Field(
        min_length=8,
        max_length=72,
        description="Password must be between 8 and 72 characters"
    )
    college: Optional[str] = Field(default=None, max_length=150)


class UserResponse(BaseModel):
    """Safe public user representation. Never exposes hashed_password."""
    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    college: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
