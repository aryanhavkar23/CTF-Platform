from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class UserDiscussionAuthor(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    role: str
    avatar_url: Optional[str] = None
    college: Optional[str] = None


class DiscussionCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Discussion title")
    content: str = Field(..., min_length=1, max_length=10000, description="Discussion markdown/text content")
    contains_spoiler: bool = Field(default=False, description="Flag indicating whether discussion contains challenge spoilers")


class DiscussionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200, description="Updated title")
    content: Optional[str] = Field(None, min_length=1, max_length=10000, description="Updated markdown/text content")
    contains_spoiler: Optional[bool] = Field(None, description="Updated spoiler status")


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Comment text or reply")
    parent_comment_id: Optional[UUID] = Field(None, description="Optional parent comment ID for threaded replies")
    contains_spoiler: bool = Field(default=False, description="Flag indicating whether comment contains challenge spoilers")


class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=5000, description="Updated comment text")
    contains_spoiler: Optional[bool] = Field(None, description="Updated spoiler status")


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    discussion_id: UUID
    user: Optional[UserDiscussionAuthor] = None
    parent_comment_id: Optional[UUID] = None
    content: str
    is_deleted: bool
    contains_spoiler: bool
    created_at: datetime
    updated_at: datetime
    replies_count: int = 0


class DiscussionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    challenge_id: UUID
    user: Optional[UserDiscussionAuthor] = None
    title: str
    content: str
    is_pinned: bool
    is_locked: bool
    is_deleted: bool
    contains_spoiler: bool
    comments_count: int = 0
    created_at: datetime
    updated_at: datetime


class DiscussionListResponse(BaseModel):
    items: List[DiscussionResponse]
    total: int
    page: int
    limit: int


class CommentListResponse(BaseModel):
    items: List[CommentResponse]
    total: int
    page: int
    limit: int
