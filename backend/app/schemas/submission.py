from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class SubmissionCreate(BaseModel):
    challenge_id: UUID
    flag: str = Field(min_length=1, max_length=255, description="Submitted flag candidate")


class SubmissionResponse(BaseModel):
    id: UUID
    challenge_id: UUID
    is_correct: bool
    points_awarded: int
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionHistoryResponse(BaseModel):
    id: UUID
    challenge_id: UUID
    challenge_title: str
    category_name: Optional[str] = None
    is_correct: bool
    points_awarded: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChallengeStatusResponse(BaseModel):
    challenge_id: UUID
    status: str  # "solved" | "attempted" | "not_attempted"
    points_earned: int
    solved_at: Optional[datetime] = None


class UserScoreResponse(BaseModel):
    user_id: UUID
    username: str
    total_points: int
    solves_count: int

    model_config = ConfigDict(from_attributes=True)
