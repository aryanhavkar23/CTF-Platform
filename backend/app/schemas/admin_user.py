from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole


class AdminUserUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    is_banned: Optional[bool] = None
    is_muted: Optional[bool] = None


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    role: UserRole
    name: Optional[str] = None
    bio: Optional[str] = None
    college: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_banned: bool
    is_muted: bool
    points: int = 0
    solves_count: int = 0
    submissions_count: int = 0
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseModel):
    items: List[AdminUserResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class AdminUserSubmissionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    challenge_id: UUID
    challenge_title: str
    is_correct: bool
    points_awarded: int
    created_at: datetime


class AdminUserDetailResponse(AdminUserResponse):
    recent_submissions: List[AdminUserSubmissionItem] = []
