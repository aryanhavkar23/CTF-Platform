from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class PeriodFilter(str, Enum):
    ALL = "all"
    TODAY = "today"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"
    NINETY_DAYS = "90d"


# -----------------------------------------------------------------------------
# Platform Overview Schemas
# -----------------------------------------------------------------------------

class PlatformOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    period: str
    total_users: int
    active_users: int
    total_challenges: int
    active_challenges: int
    total_submissions: int
    correct_submissions: int
    incorrect_submissions: int
    total_solves: int
    total_teams: int
    active_teams: int
    total_events: int
    completed_events: int
    total_badges_awarded: int
    total_discussions: int


# -----------------------------------------------------------------------------
# User Analytics Schemas
# -----------------------------------------------------------------------------

class CollegeCountItem(BaseModel):
    college: str
    count: int


class RoleCountItem(BaseModel):
    role: str
    count: int


class UserAnalyticsResponse(BaseModel):
    period: str
    total_users: int
    new_users: int
    active_users: int
    users_with_solves: int
    users_without_solves: int
    by_college: List[CollegeCountItem]
    by_role: List[RoleCountItem]


# -----------------------------------------------------------------------------
# User Activity Trend Schemas
# -----------------------------------------------------------------------------

class ActivityTrendPoint(BaseModel):
    date: str
    activities: int


class ActivityTrendResponse(BaseModel):
    period: str
    data: List[ActivityTrendPoint]


# -----------------------------------------------------------------------------
# Challenge & Difficulty Analytics Schemas
# -----------------------------------------------------------------------------

class ChallengeAnalyticsItem(BaseModel):
    challenge_id: UUID
    title: str
    category: str
    difficulty: str
    points: int
    total_attempts: int
    correct_attempts: int
    unique_solvers: int
    solve_rate: float


class DifficultyAnalyticsItem(BaseModel):
    difficulty: str
    challenge_count: int
    attempts: int
    solves: int
    average_solve_rate: float


class ChallengeInsightsResponse(BaseModel):
    min_attempts_threshold: int
    most_difficult: List[ChallengeAnalyticsItem]
    most_solved: List[ChallengeAnalyticsItem]
    most_attempted: List[ChallengeAnalyticsItem]


# -----------------------------------------------------------------------------
# Category Analytics Schemas
# -----------------------------------------------------------------------------

class CategoryAnalyticsItem(BaseModel):
    category_id: UUID
    category_name: str
    challenge_count: int
    attempts: int
    solves: int
    unique_solvers: int
    total_points_awarded: int
    average_solve_rate: float


# -----------------------------------------------------------------------------
# Submission Analytics Schemas
# -----------------------------------------------------------------------------

class SubmissionDayPoint(BaseModel):
    date: str
    total: int
    correct: int
    incorrect: int


class ChallengeFailureItem(BaseModel):
    challenge_id: UUID
    title: str
    failure_rate: float
    attempts: int


class FrequentSubmitterItem(BaseModel):
    user_id: UUID
    username: str
    submission_count: int


class SubmissionAnalyticsResponse(BaseModel):
    period: str
    total_submissions: int
    correct_submissions: int
    incorrect_submissions: int
    accuracy_rate: float
    unique_submitters: int
    average_attempts_before_solve: float
    submissions_by_day: List[SubmissionDayPoint]
    challenges_highest_failure: List[ChallengeFailureItem]
    frequent_submitters: List[FrequentSubmitterItem]


# -----------------------------------------------------------------------------
# Event Analytics Schemas
# -----------------------------------------------------------------------------

class EventAnalyticsItem(BaseModel):
    event_id: UUID
    name: str
    slug: str
    status: str
    registration_count: int
    active_participants: int
    challenges_assigned: int
    total_submissions: int
    total_solves: int
    is_scoreboard_frozen: bool = False


class EventPerformanceChallengeItem(BaseModel):
    challenge_id: UUID
    title: str
    attempts: int
    solves: int
    solve_rate: float


class EventTopParticipant(BaseModel):
    participant_id: UUID
    name: str
    registration_type: str
    score: int
    solves: int


class EventDetailAnalyticsResponse(BaseModel):
    event_id: UUID
    name: str
    slug: str
    status: str
    total_registrations: int
    individual_registrations: int
    team_registrations: int
    unique_participants: int
    total_submissions: int
    total_solves: int
    participation_rate: float
    challenge_performance: List[EventPerformanceChallengeItem]
    top_participants: List[EventTopParticipant]


# -----------------------------------------------------------------------------
# Team Analytics Schemas
# -----------------------------------------------------------------------------

class TeamAnalyticsResponse(BaseModel):
    total_teams: int
    active_teams: int
    average_team_size: float
    by_college: List[CollegeCountItem]
    teams_with_solves: int
    teams_without_solves: int


# -----------------------------------------------------------------------------
# Badge Analytics Schemas
# -----------------------------------------------------------------------------

class BadgeAnalyticsItem(BaseModel):
    badge_id: UUID
    name: str
    slug: str
    icon: str
    awarded_count: int


class BadgeAnalyticsResponse(BaseModel):
    total_badge_definitions: int
    total_badges_awarded: int
    most_awarded_badges: List[BadgeAnalyticsItem]
    least_awarded_badges: List[BadgeAnalyticsItem]


# -----------------------------------------------------------------------------
# Discussion Analytics Schemas
# -----------------------------------------------------------------------------

class MostDiscussedChallengeItem(BaseModel):
    challenge_id: UUID
    title: str
    thread_count: int
    comment_count: int


class DiscussionAnalyticsResponse(BaseModel):
    period: str
    total_discussions: int
    total_comments: int
    period_discussions: int
    period_comments: int
    locked_discussions: int
    deleted_discussions: int
    most_discussed_challenges: List[MostDiscussedChallengeItem]


# -----------------------------------------------------------------------------
# Leaderboard Insights Schemas
# -----------------------------------------------------------------------------

class ScoreRangeItem(BaseModel):
    min: int
    max: Optional[int] = None
    label: str
    users: int


class TopUserItem(BaseModel):
    rank: int
    user_id: UUID
    username: str
    college: Optional[str] = None
    score: int
    solves: int


class LeaderboardAnalyticsResponse(BaseModel):
    ranked_users_count: int
    average_score: float
    median_score: float
    score_distribution: List[ScoreRangeItem]
    top_users: List[TopUserItem]


# -----------------------------------------------------------------------------
# Dashboard Composite Summary Schema
# -----------------------------------------------------------------------------

class DashboardAnalyticsResponse(BaseModel):
    overview: PlatformOverviewResponse
    activity_trend: List[ActivityTrendPoint]
    category_summary: List[CategoryAnalyticsItem]
    difficulty_summary: List[DifficultyAnalyticsItem]
    top_challenges: List[ChallengeAnalyticsItem]
    event_summary: List[EventAnalyticsItem]
