from datetime import date
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_active_user, get_current_user_optional
from app.schemas.profile import (
    ProfileUpdate,
    PublicProfileResponse,
    PrivateProfileResponse,
    SolvedChallengeResponse,
    ActivityResponse,
    ActivityListResponse,
    HeatmapDayResponse,
    StreakResponse,
    CategoryStatsResponse,
)
from app.schemas.badge import UserBadgeResponse, BadgeProgressResponse
from app.services.profile_service import ProfileService
from app.services.activity_service import ActivityService
from app.services.streak_service import StreakService
from app.services.badge_service import BadgeService

router = APIRouter(prefix="/api/profile", tags=["Profiles"])


def _resolve_target_user(db: Session, user_id: UUID) -> User:
    """Helper to find and validate an active user by ID, or raise 404."""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or is inactive"
        )
    return user


# ==========================================
# /me ENDPOINTS (Authenticated Current User)
# ==========================================

@router.get("/me", response_model=PrivateProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve detailed private profile for the currently authenticated user."""
    data = ProfileService.get_profile(db, current_user, is_self=True)
    return PrivateProfileResponse(**data)


@router.put("/me", response_model=PrivateProfileResponse)
def update_my_profile(
    update_data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update profile fields (name, bio, college, avatar_url) for current user.
    
    Security note: Role, permissions, points, and ranks cannot be modified here.
    """
    updated_user = ProfileService.update_profile(db, current_user, update_data)
    data = ProfileService.get_profile(db, updated_user, is_self=True)
    return PrivateProfileResponse(**data)


@router.get("/me/solved", response_model=List[SolvedChallengeResponse])
def get_my_solved_challenges(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve solved challenge history for the currently authenticated user."""
    return ProfileService.get_user_solved_challenges(db, current_user.id)


@router.get("/me/activity", response_model=ActivityListResponse)
def get_my_activity(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve paginated activity history for the currently authenticated user."""
    items, total = ActivityService.get_user_activities(db, current_user.id, page=page, limit=limit)
    return ActivityListResponse(
        page=page,
        limit=limit,
        total=total,
        items=[ActivityResponse(**item) for item in items]
    )


@router.get("/me/activity/heatmap", response_model=List[HeatmapDayResponse])
def get_my_activity_heatmap(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve daily activity counts for GitHub-style heatmap generation."""
    return ActivityService.get_activity_heatmap(db, current_user.id, start_date=start_date, end_date=end_date)


@router.get("/me/streak", response_model=StreakResponse)
def get_my_streak(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve current and longest CTF streak metrics for the authenticated user."""
    return StreakService.get_user_streak(db, current_user.id)


@router.get("/me/category-stats", response_model=List[CategoryStatsResponse])
def get_my_category_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve category-level solve count and point breakdowns for authenticated user."""
    return ProfileService.get_user_category_stats(db, current_user.id)


@router.get("/me/badges", response_model=List[UserBadgeResponse])
def get_my_badges(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[UserBadgeResponse]:
    """Retrieve all unlocked achievements and badges for authenticated user."""
    badges_data = BadgeService.get_user_badges(db, current_user.id)
    return [UserBadgeResponse(**b) for b in badges_data]


@router.get("/me/badge-progress", response_model=List[BadgeProgressResponse])
def get_my_badge_progress(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[BadgeProgressResponse]:
    """Retrieve authoritative unlock progress towards all active badges."""
    progress_data = BadgeService.get_user_badge_progress(db, current_user.id)
    return [BadgeProgressResponse(**p) for p in progress_data]


@router.get("/me/badges/{badge_id}/progress", response_model=BadgeProgressResponse)
def get_my_single_badge_progress(
    badge_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> BadgeProgressResponse:
    """Retrieve authoritative unlock progress for a specific badge."""
    prog = BadgeService.get_single_badge_progress(db, current_user.id, badge_id)
    return BadgeProgressResponse(**prog)


# ==========================================
# PUBLIC PROFILE ENDPOINTS (by user_id)
# ==========================================

@router.get("/{user_id}", response_model=PublicProfileResponse)
def get_public_profile(
    user_id: UUID,
    db: Session = Depends(get_db),
    _caller: Optional[User] = Depends(get_current_user_optional)
):
    """Retrieve public profile with CTF stats for any active user."""
    target_user = _resolve_target_user(db, user_id)
    data = ProfileService.get_profile(db, target_user, is_self=False)
    return PublicProfileResponse(**data)


@router.get("/{user_id}/solved", response_model=List[SolvedChallengeResponse])
def get_public_user_solved_challenges(
    user_id: UUID,
    db: Session = Depends(get_db),
    _caller: Optional[User] = Depends(get_current_user_optional)
):
    """Retrieve verified solved challenges for a specific user without sensitive details."""
    target_user = _resolve_target_user(db, user_id)
    return ProfileService.get_user_solved_challenges(db, target_user.id)


@router.get("/{user_id}/activity", response_model=ActivityListResponse)
def get_public_user_activity(
    user_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _caller: Optional[User] = Depends(get_current_user_optional)
):
    """Retrieve paginated public CTF activity feed for a specific user."""
    target_user = _resolve_target_user(db, user_id)
    items, total = ActivityService.get_user_activities(db, target_user.id, page=page, limit=limit)
    return ActivityListResponse(
        page=page,
        limit=limit,
        total=total,
        items=[ActivityResponse(**item) for item in items]
    )


@router.get("/{user_id}/activity/heatmap", response_model=List[HeatmapDayResponse])
def get_public_user_activity_heatmap(
    user_id: UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _caller: Optional[User] = Depends(get_current_user_optional)
):
    """Retrieve daily activity counts for heatmap generation for a specific user."""
    target_user = _resolve_target_user(db, user_id)
    return ActivityService.get_activity_heatmap(db, target_user.id, start_date=start_date, end_date=end_date)


@router.get("/{user_id}/streak", response_model=StreakResponse)
def get_public_user_streak(
    user_id: UUID,
    db: Session = Depends(get_db),
    _caller: Optional[User] = Depends(get_current_user_optional)
):
    """Retrieve streak statistics for a specific user."""
    target_user = _resolve_target_user(db, user_id)
    return StreakService.get_user_streak(db, target_user.id)


@router.get("/{user_id}/category-stats", response_model=List[CategoryStatsResponse])
def get_public_user_category_stats(
    user_id: UUID,
    db: Session = Depends(get_db),
    _caller: Optional[User] = Depends(get_current_user_optional)
):
    """Retrieve category-level statistics for a specific user."""
    target_user = _resolve_target_user(db, user_id)
    return ProfileService.get_user_category_stats(db, target_user.id)


@router.get("/{user_id}/badges", response_model=List[UserBadgeResponse])
def get_public_user_badges(
    user_id: UUID,
    db: Session = Depends(get_db),
    _caller: Optional[User] = Depends(get_current_user_optional)
) -> List[UserBadgeResponse]:
    """Retrieve all unlocked achievements and badges for a specific user."""
    target_user = _resolve_target_user(db, user_id)
    badges_data = BadgeService.get_user_badges(db, target_user.id)
    return [UserBadgeResponse(**b) for b in badges_data]
