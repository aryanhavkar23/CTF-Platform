from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class FollowStatusResponse(BaseModel):
    user_id: UUID
    is_following: bool
    followers_count: int
    following_count: int


class FollowUserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    name: Optional[str] = None
    college: Optional[str] = None
    avatar_url: Optional[str] = None
    total_points: int = 0
    solves_count: int = 0
    is_following: bool = False
    followed_at: datetime


class FollowersListResponse(BaseModel):
    total: int
    users: List[FollowUserItem]
