import re
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from app.models.user import UserRole


GITHUB_URL_REGEX = re.compile(
    r"^https?://(www\.)?github\.com/([a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38})/?$",
    re.IGNORECASE
)


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
    github_profile_url: Optional[str] = Field(
        default=None,
        description="Valid student GitHub profile URL, e.g. https://github.com/username",
        max_length=255
    )

    @field_validator("github_profile_url")
    @classmethod
    def validate_github_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            return None
        if clean.startswith("github.com/"):
            clean = "https://" + clean
        elif not clean.startswith("http://") and not clean.startswith("https://") and "/" not in clean:
            clean = f"https://github.com/{clean}"
        elif not clean.startswith("http://") and not clean.startswith("https://"):
            clean = "https://" + clean

        match = GITHUB_URL_REGEX.match(clean)
        if not match:
            raise ValueError("Must be a valid GitHub profile URL (e.g. https://github.com/username)")
        return clean.rstrip("/")


class UserResponse(BaseModel):
    """Safe public user representation. Never exposes hashed_password."""
    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    college: Optional[str] = None
    avatar_url: Optional[str] = None
    github_profile_url: Optional[str] = None
    github_username: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
