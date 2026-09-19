import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict


def sanitize_text(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    # Strip dangerous HTML tags
    cleaned = re.sub(r"<[^>]*?>", "", v).strip()
    return cleaned


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    college: Optional[str] = Field(None, max_length=150)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=512)

    @field_validator("name", "college", "bio", mode="before")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_text(v)

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_strip = v.strip()
        if v_strip.lower().startswith("javascript:"):
            raise ValueError("Invalid avatar URL scheme")
        return v_strip


class PublicProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    name: Optional[str] = None
    college: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    total_points: int = 0
    global_rank: Optional[int] = None
    college_rank: Optional[int] = None
    challenges_solved: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    events_participated: int = 0
    current_team: Optional[str] = None
    badges_count: int = 0
    recent_badges: List[Dict[str, Any]] = Field(default_factory=list)
    followers_count: int = 0
    following_count: int = 0
    is_following: bool = False


class PrivateProfileResponse(PublicProfileResponse):
    email: str
    role: str
    is_verified: bool


class SolvedChallengeResponse(BaseModel):
    challenge_id: UUID
    challenge_title: str
    category: str
    difficulty: str
    points_awarded: int
    solved_at: datetime


class ActivityResponse(BaseModel):
    id: UUID
    user_id: UUID
    activity_type: str
    reference_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ActivityListResponse(BaseModel):
    page: int
    limit: int
    total: int
    items: List[ActivityResponse]


class HeatmapDayResponse(BaseModel):
    date: str
    count: int


class StreakResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_active_date: Optional[str] = None


class CategoryStatsResponse(BaseModel):
    category: str
    solved_count: int
    points_earned: int
    total_count: Optional[int] = 0
