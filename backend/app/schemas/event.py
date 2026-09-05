import re
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=150, description="Event name")
    description: Optional[str] = Field(None, max_length=2000, description="Event overview / rules")
    slug: Optional[str] = Field(None, max_length=150, description="URL-friendly slug (auto-generated if omitted)")
    start_at: datetime = Field(..., description="Event start timestamp (UTC)")
    end_at: datetime = Field(..., description="Event end timestamp (UTC)")
    registration_start_at: Optional[datetime] = Field(None, description="Registration opens (UTC)")
    registration_end_at: Optional[datetime] = Field(None, description="Registration closes (UTC)")
    status: Optional[str] = Field("upcoming", description="Initial status")
    is_active: Optional[bool] = True

    @model_validator(mode="after")
    def validate_event_dates(self):
        # 1. Start before End
        if self.end_at <= self.start_at:
            raise ValueError("Event end_at must be strictly after start_at.")

        # 2. Registration sequence if provided
        if self.registration_start_at and self.registration_end_at:
            if self.registration_end_at <= self.registration_start_at:
                raise ValueError("registration_end_at must be after registration_start_at.")
            if self.registration_end_at > self.start_at:
                raise ValueError("registration_end_at must be less than or equal to event start_at.")
        elif self.registration_start_at or self.registration_end_at:
            raise ValueError("Both registration_start_at and registration_end_at must be provided together.")

        # Auto-generate slug if omitted
        if not self.slug:
            cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", self.name).strip().lower()
            self.slug = re.sub(r"[\s-]+", "-", cleaned) or "ctf-event"

        return self


class EventUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = Field(None, max_length=2000)
    slug: Optional[str] = Field(None, max_length=150)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    registration_start_at: Optional[datetime] = None
    registration_end_at: Optional[datetime] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class EventChallengeAdd(BaseModel):
    challenge_id: UUID = Field(..., description="ID of the challenge to add to the event")
    display_order: Optional[int] = Field(1, ge=1, description="Display order within the event")
    points_override: Optional[int] = Field(None, ge=0, description="Optional points override for this event")


class EventChallengeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    category_id: UUID
    category_name: Optional[str] = None
    difficulty: str
    points: int
    display_order: int
    is_active: bool


class EventRegistrationRequest(BaseModel):
    registration_type: str = Field(..., pattern="^(individual|team)$", description="'individual' or 'team'")
    team_id: Optional[UUID] = Field(None, description="Required if registration_type is 'team'")

    @model_validator(mode="after")
    def validate_type(self):
        if self.registration_type == "team" and not self.team_id:
            raise ValueError("team_id is required for team registration.")
        if self.registration_type == "individual" and self.team_id is not None:
            raise ValueError("team_id must be null for individual registration.")
        return self


class EventRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    user_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    participant_name: str
    registration_type: str
    registered_at: datetime
    is_active: bool


class EventParticipantResponse(BaseModel):
    id: UUID
    registration_type: str
    participant_id: UUID
    participant_name: str
    college: Optional[str] = None
    registered_at: datetime


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    slug: str
    start_at: datetime
    end_at: datetime
    registration_start_at: Optional[datetime] = None
    registration_end_at: Optional[datetime] = None
    status: str
    computed_status: str
    is_registration_open: bool
    is_active: bool
    is_scoreboard_frozen: bool
    scoreboard_frozen_at: Optional[datetime] = None
    challenge_count: int = 0
    participant_count: int = 0
    created_at: datetime
    updated_at: datetime


class EventLeaderboardEntry(BaseModel):
    rank: int
    participant_id: UUID
    participant_name: str
    participant_type: str  # "individual" or "team"
    college: Optional[str] = None
    total_points: int
    solved_count: int
    last_solve_time: Optional[datetime] = None


class EventLeaderboardResponse(BaseModel):
    event_id: UUID
    event_name: str
    is_scoreboard_frozen: bool
    is_frozen: Optional[bool] = None
    scoreboard_frozen_at: Optional[datetime] = None
    frozen_at: Optional[datetime] = None
    total_participants: int
    items: List[EventLeaderboardEntry] = []
    entries: List[EventLeaderboardEntry] = []

    @model_validator(mode="after")
    def sync_aliases(self):
        if self.is_frozen is None:
            self.is_frozen = self.is_scoreboard_frozen
        if self.frozen_at is None:
            self.frozen_at = self.scoreboard_frozen_at
        if not self.entries and self.items:
            self.entries = self.items
        elif not self.items and self.entries:
            self.items = self.entries
        return self
