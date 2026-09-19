from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.models.security_event import (
    SecurityEventType,
    SecurityEventSeverity,
    SecurityEventStatus,
)


class SecurityEventReviewRequest(BaseModel):
    status: SecurityEventStatus
    note: Optional[str] = Field(default=None, max_length=1000)


class SecurityEventReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    security_event_id: UUID
    reviewer_id: Optional[UUID] = None
    reviewer_username: Optional[str] = None
    previous_status: str
    new_status: str
    note: Optional[str] = None
    created_at: datetime


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    team_id: Optional[UUID] = None
    team_name: Optional[str] = None
    event_id: Optional[UUID] = None
    event_name: Optional[str] = None
    challenge_id: Optional[UUID] = None
    challenge_title: Optional[str] = None
    event_type: str
    severity: str
    description: str
    metadata_json: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    reviews: List[SecurityEventReviewResponse] = Field(default_factory=list)


class SecurityEventListResponse(BaseModel):
    items: List[SecurityEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserSecuritySummaryResponse(BaseModel):
    user_id: UUID
    username: str
    total_security_events: int
    open_events: int
    high_critical_events: int
    suspicion_score: int
    suspicion_level: str
    recent_events: List[SecurityEventResponse]
