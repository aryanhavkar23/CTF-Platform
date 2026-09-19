from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Team name (unique)")
    description: Optional[str] = Field(None, max_length=1000, description="Team description or bio")
    college: Optional[str] = Field(None, max_length=150, description="Affiliated college/university")


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    college: Optional[str] = Field(None, max_length=150)
    is_active: Optional[bool] = None


class AddTeamMemberRequest(BaseModel):
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    role: Optional[str] = "member"

    @model_validator(mode="after")
    def validate_user_identifier(self):
        if not self.user_id and not self.username:
            raise ValueError("Either user_id or username must be provided.")
        return self


class TransferOwnershipRequest(BaseModel):
    new_owner_id: UUID = Field(..., description="UUID of the active team member to become owner")


class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    user_id: UUID
    username: str
    college: Optional[str] = None
    role: str
    is_active: bool
    joined_at: datetime


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    college: Optional[str] = None
    owner_id: UUID
    owner_username: Optional[str] = None
    member_count: int = 0
    max_team_size: int = 4
    is_active: bool
    invite_code: Optional[str] = None
    join_code: Optional[str] = None
    total_points: Optional[int] = 0
    created_at: datetime
    updated_at: datetime


class TeamDetailResponse(TeamResponse):
    members: List[TeamMemberResponse] = []


class UserTeamDetailResponse(TeamDetailResponse):
    my_role: str = "member"  # "owner", "captain", "member"
    events_participated_count: int = 0


class TeamEventSolveItem(BaseModel):
    challenge_id: UUID
    challenge_title: str
    category: Optional[str] = None
    points_awarded: int
    solver_username: Optional[str] = None
    solved_at: datetime


class TeamEventHistoryItem(BaseModel):
    event_id: UUID
    event_name: str
    event_slug: Optional[str] = None
    status: str
    start_at: datetime
    end_at: datetime
    score: int = 0
    solves_count: int = 0
    rank: Optional[int] = None
    total_teams: Optional[int] = None
    registered_at: Optional[datetime] = None
    solves: List[TeamEventSolveItem] = []


class TeamHistoryResponse(BaseModel):
    team_id: UUID
    team_name: str
    college: Optional[str] = None
    description: Optional[str] = None
    owner_username: Optional[str] = None
    member_count: int = 0
    members: List[TeamMemberResponse] = []
    events_participated_count: int = 0
    total_score: int = 0
    total_solves: int = 0
    events: List[TeamEventHistoryItem] = []
