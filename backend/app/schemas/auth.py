from typing import Optional
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


class ChangePasswordRequest(BaseModel):
    """Schema for authenticated password change."""
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=72)


class ForgotPasswordRequest(BaseModel):
    """Schema for requesting a password reset email/token."""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Schema returned upon password reset dispatch."""
    message: str
    reset_token: Optional[str] = None  # Included in development/testing mode for verification


class ResetPasswordRequest(BaseModel):
    """Schema for setting a new password using a reset token."""
    reset_token: str
    new_password: str = Field(min_length=8, max_length=72)


class GoogleAuthUrlResponse(BaseModel):
    """Schema returning the Google OAuth authorization URL."""
    auth_url: str


class GoogleOAuthCallbackRequest(BaseModel):
    """Schema for exchanging Google auth tokens or simulated credentials."""
    code: Optional[str] = None
    id_token: Optional[str] = None
    # Simulated mock parameters for zero-budget local testing without cloud credentials
    mock_email: Optional[EmailStr] = None
    mock_name: Optional[str] = None
    mock_sub: Optional[str] = None
