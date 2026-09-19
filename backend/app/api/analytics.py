from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.api.deps import require_role
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    PeriodFilter,
    PlatformOverviewResponse,
    UserAnalyticsResponse,
    ActivityTrendResponse,
    ChallengeAnalyticsItem,
    DifficultyAnalyticsItem,
    ChallengeInsightsResponse,
    CategoryAnalyticsItem,
    SubmissionAnalyticsResponse,
    EventAnalyticsItem,
    EventDetailAnalyticsResponse,
    TeamAnalyticsResponse,
    BadgeAnalyticsResponse,
    DiscussionAnalyticsResponse,
    LeaderboardAnalyticsResponse,
    DashboardAnalyticsResponse,
)

router = APIRouter(
    prefix="/api/admin/analytics",
    tags=["Admin Analytics"],
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))]
)


@router.get("/overview", response_model=PlatformOverviewResponse)
def get_overview(
    period: PeriodFilter = Query(default=PeriodFilter.ALL),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns high-level platform health and volume metrics."""
    return AnalyticsService.get_platform_overview(db, period)


@router.get("/users", response_model=UserAnalyticsResponse)
def get_users(
    period: PeriodFilter = Query(default=PeriodFilter.ALL),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns user growth, demographics, and solve status breakdowns."""
    return AnalyticsService.get_user_analytics(db, period)


@router.get("/activity", response_model=ActivityTrendResponse)
def get_activity_trend(
    period: PeriodFilter = Query(default=PeriodFilter.THIRTY_DAYS),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns daily activity event frequencies."""
    return AnalyticsService.get_activity_trend(db, period)


@router.get("/challenges", response_model=List[ChallengeAnalyticsItem])
def get_challenge_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns attempt and solve rate aggregates for all challenges."""
    return AnalyticsService.get_challenge_analytics(db)


@router.get("/challenges/difficulty", response_model=List[DifficultyAnalyticsItem])
def get_difficulty_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns aggregated solve rates and attempt volumes grouped by challenge difficulty."""
    return AnalyticsService.get_difficulty_analytics(db)


@router.get("/challenges/insights", response_model=ChallengeInsightsResponse)
def get_challenge_insights(
    min_attempts: int = Query(default=10, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns ranked lists of most difficult, most solved, and most attempted challenges."""
    return AnalyticsService.get_challenge_insights(db, min_attempts)


@router.get("/categories", response_model=List[CategoryAnalyticsItem])
def get_category_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns challenge, attempt, solver, and point distribution across categories."""
    return AnalyticsService.get_category_analytics(db)


@router.get("/submissions", response_model=SubmissionAnalyticsResponse)
def get_submission_analytics(
    period: PeriodFilter = Query(default=PeriodFilter.ALL),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns submission volumes, accuracy rates, daily breakdown, and high-failure challenges."""
    return AnalyticsService.get_submission_analytics(db, period)


@router.get("/events", response_model=List[EventAnalyticsItem])
def get_events_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns participation and volume metrics across all CTF events."""
    return AnalyticsService.get_events_analytics(db)


@router.get("/events/{event_id}", response_model=EventDetailAnalyticsResponse)
def get_event_detail_analytics(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns granular participation, challenge performance, and leaderboard data for an event."""
    result = AnalyticsService.get_event_detail_analytics(db, event_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        )
    return result


@router.get("/teams", response_model=TeamAnalyticsResponse)
def get_team_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns team roster sizes, college distributions, and solve activity."""
    return AnalyticsService.get_team_analytics(db)


@router.get("/badges", response_model=BadgeAnalyticsResponse)
def get_badge_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns distribution and award frequency for badges."""
    return AnalyticsService.get_badge_analytics(db)


@router.get("/discussions", response_model=DiscussionAnalyticsResponse)
def get_discussion_analytics(
    period: PeriodFilter = Query(default=PeriodFilter.ALL),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns forum discussion activity, comment volumes, and moderation statistics."""
    return AnalyticsService.get_discussion_analytics(db, period)


@router.get("/leaderboard", response_model=LeaderboardAnalyticsResponse)
def get_leaderboard_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns score distributions, mean/median scores, and top ranked competitors."""
    return AnalyticsService.get_leaderboard_insights(db)


@router.get("/dashboard", response_model=DashboardAnalyticsResponse)
def get_dashboard_summary(
    period: PeriodFilter = Query(default=PeriodFilter.THIRTY_DAYS),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MODERATOR))
):
    """Returns a composite platform summary for the admin analytics dashboard."""
    return AnalyticsService.get_dashboard_summary(db, period)
