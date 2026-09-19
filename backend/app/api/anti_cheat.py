from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.api.deps import require_role
from app.services.anti_cheat_service import AntiCheatService
from app.schemas.security_event import (
    SecurityEventResponse,
    SecurityEventListResponse,
    SecurityEventReviewRequest,
    UserSecuritySummaryResponse,
)

# Primary router mounted at /api/admin
router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Anti-Cheat & Security"],
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))]
)


@router.get("/security-events", response_model=SecurityEventListResponse)
@router.get("/security/events", response_model=SecurityEventListResponse)
def list_security_events(
    status: Optional[str] = Query(None, description="Filter by status (open, reviewed, dismissed, actioned)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low, medium, high, critical)"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    event_id: Optional[UUID] = Query(None, description="Filter by CTF event ID"),
    start_date: Optional[datetime] = Query(None, description="Filter incidents starting from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter incidents up to this date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Retrieves paginated anti-cheat security incidents with multi-dimensional filtering."""
    return AntiCheatService.list_security_events(
        db=db,
        status=status,
        severity=severity,
        event_type=event_type,
        user_id=user_id,
        event_id=event_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get("/security-events/{event_id}", response_model=SecurityEventResponse)
@router.get("/security/events/{event_id}", response_model=SecurityEventResponse)
def get_security_event_detail(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Retrieves detailed information and review history for a single security incident."""
    event = AntiCheatService.get_security_event_detail(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security event not found"
        )
    return event


@router.post("/security-events/{event_id}/review", response_model=SecurityEventResponse)
@router.post("/security/events/{event_id}/review", response_model=SecurityEventResponse)
def review_security_event(
    event_id: UUID,
    payload: SecurityEventReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Transitions a security event status with an immutable moderator audit trail entry."""
    return AntiCheatService.review_security_event(
        db=db,
        event_id=event_id,
        reviewer_id=current_user.id,
        new_status=payload.status,
        note=payload.note,
    )


@router.get("/security/users/{user_id}", response_model=UserSecuritySummaryResponse)
def get_user_security_summary(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR)),
):
    """Provides administrators with an aggregated risk evaluation and suspicion score for a user."""
    return AntiCheatService.get_user_security_summary(db, user_id)
