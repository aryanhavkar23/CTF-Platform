from pydantic import BaseModel, EmailStr, Field
from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    """Schema for user authentication credentials."""
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Schema for successful authentication response containing JWT and user profile."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
