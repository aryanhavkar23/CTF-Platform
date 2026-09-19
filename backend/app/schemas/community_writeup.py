from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class UserWriteupCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=10)
    tags: Optional[str] = Field(None, max_length=255)


class UserWriteupUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    tags: Optional[str] = Field(None, max_length=255)
    is_published: Optional[bool] = None


class UserWriteupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    challenge_id: UUID
    user_id: UUID
    title: str
    content: str
    tags: Optional[str] = None
    upvotes_count: int = 0
    is_published: bool = True
    created_at: datetime
    updated_at: datetime

    # Author details
    author_username: str
    author_name: Optional[str] = None
    author_college: Optional[str] = None
    author_avatar_url: Optional[str] = None
    author_has_solved: bool = False

    # Caller context
    is_upvoted_by_me: bool = False
    is_author: bool = False

    # Target Challenge details
    challenge_title: Optional[str] = None
    challenge_category: Optional[str] = None
    challenge_points: Optional[int] = None


class WriteupUpvoteResponse(BaseModel):
    writeup_id: UUID
    upvotes_count: int
    is_upvoted: bool
