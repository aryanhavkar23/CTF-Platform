from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.api.deps import get_current_user, get_current_user_optional, require_role
from app.schemas.badge import (
    BadgeCreate,
    BadgeUpdate,
    BadgeResponse,
    BadgeStatsResponse,
    BadgeUserItem,
)
from app.services.badge_service import BadgeService

router = APIRouter(prefix="/api/badges", tags=["Badges"])


@router.post(
    "",
    response_model=BadgeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new badge definition (Admin only)"
)
def create_badge(
    badge_in: BadgeCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN))
) -> BadgeResponse:
    """Creates a new badge definition in the platform database."""
    badge = BadgeService.create_badge(db, badge_in)
    return BadgeResponse.model_validate(badge)


@router.get(
    "",
    response_model=List[BadgeResponse],
    summary="List available badge definitions"
)
def list_badges(
    include_inactive: bool = Query(False, description="Include inactive badges (admin only)"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> List[BadgeResponse]:
    """Lists badge definitions. Inactive badges are only returned if caller is an admin and requests them."""
    is_admin = current_user and current_user.role == UserRole.ADMIN
    show_inactive = include_inactive and is_admin
    badges = BadgeService.list_badges(db, include_inactive=show_inactive)
    return [BadgeResponse.model_validate(b) for b in badges]


@router.get(
    "/{badge_id}",
    response_model=BadgeResponse,
    summary="Retrieve badge definition by ID or slug"
)
def get_badge(
    badge_id: str,
    db: Session = Depends(get_db)
) -> BadgeResponse:
    """Retrieves a single badge by its UUID or unique slug."""
    badge = BadgeService.get_badge(db, badge_id)
    return BadgeResponse.model_validate(badge)


@router.put(
    "/{badge_id}",
    response_model=BadgeResponse,
    summary="Update badge definition (Admin only)"
)
def update_badge(
    badge_id: UUID,
    badge_in: BadgeUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN))
) -> BadgeResponse:
    """Modifies attributes of an existing badge definition."""
    badge = BadgeService.update_badge(db, badge_id, badge_in)
    return BadgeResponse.model_validate(badge)


@router.delete(
    "/{badge_id}",
    summary="Delete or deactivate badge definition (Admin only)"
)
def delete_badge(
    badge_id: UUID,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN))
):
    """
    Deactivates badge if users have already earned it to protect user history;
    hard deletes badge if it has never been awarded.
    """
    deleted, message = BadgeService.delete_or_deactivate_badge(db, badge_id)
    return {
        "success": True,
        "action": "deleted" if deleted else "deactivated",
        "message": message,
    }


@router.get(
    "/{badge_id}/users",
    response_model=List[BadgeUserItem],
    summary="List users who have earned this badge (Admin only)"
)
def get_badge_users(
    badge_id: UUID,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_role(UserRole.ADMIN))
) -> List[BadgeUserItem]:
    """Retrieves the list of users who have earned this badge."""
    users_data = BadgeService.get_badge_users(db, badge_id)
    return [BadgeUserItem(**item) for item in users_data]


@router.get(
    "/{badge_id}/stats",
    response_model=BadgeStatsResponse,
    summary="Get summary stats for a badge"
)
def get_badge_stats(
    badge_id: UUID,
    db: Session = Depends(get_db)
) -> BadgeStatsResponse:
    """Returns total user awards count for a badge."""
    stats = BadgeService.get_badge_stats(db, badge_id)
    return BadgeStatsResponse(**stats)
