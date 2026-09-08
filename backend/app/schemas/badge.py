import re
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.models.badge import CriteriaType


class BadgeBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    slug: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=5, max_length=500)
    icon: str = Field(..., min_length=1, max_length=255)
    criteria_type: str = Field(...)
    criteria_value: int = Field(default=1, ge=0)
    is_active: bool = True

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if not re.match(r"^[a-z0-9_-]+$", v_clean):
            raise ValueError("Slug must contain only lowercase alphanumeric characters, dashes, or underscores.")
        return v_clean

    @field_validator("criteria_type")
    @classmethod
    def validate_criteria_type(cls, v: str) -> str:
        valid_types = {t.value for t in CriteriaType}
        v_clean = v.strip().lower()
        if v_clean not in valid_types:
            raise ValueError(f"Invalid criteria_type. Must be one of: {sorted(list(valid_types))}")
        return v_clean


class BadgeCreate(BadgeBase):
    pass


class BadgeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, min_length=5, max_length=500)
    icon: Optional[str] = Field(None, min_length=1, max_length=255)
    criteria_type: Optional[str] = None
    criteria_value: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @field_validator("slug")
    @classmethod
    def validate_slug_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip().lower()
        if not re.match(r"^[a-z0-9_-]+$", v_clean):
            raise ValueError("Slug must contain only lowercase alphanumeric characters, dashes, or underscores.")
        return v_clean

    @field_validator("criteria_type")
    @classmethod
    def validate_criteria_type_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        valid_types = {t.value for t in CriteriaType}
        v_clean = v.strip().lower()
        if v_clean not in valid_types:
            raise ValueError(f"Invalid criteria_type. Must be one of: {sorted(list(valid_types))}")
        return v_clean


class BadgeResponse(BadgeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class UserBadgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    badge_id: UUID
    name: str
    slug: str
    description: str
    icon: str
    awarded_at: datetime


class BadgeProgressResponse(BaseModel):
    badge_id: UUID
    name: str
    slug: str
    description: str
    icon: str
    criteria_type: str
    current_value: int
    required_value: int
    progress_percentage: float
    is_unlocked: bool


class BadgeStatsResponse(BaseModel):
    badge_id: UUID
    name: str
    slug: str
    total_users_awarded: int


class BadgeUserItem(BaseModel):
    user_id: UUID
    username: str
    name: Optional[str] = None
    college: Optional[str] = None
    avatar_url: Optional[str] = None
    awarded_at: datetime
