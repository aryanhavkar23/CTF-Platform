from app.database import Base
from app.models.base import TimeStampedModel
from app.models.user import User, UserRole
from app.models.team import Team, TeamMember, team_members
from app.models.category import Category
from app.models.challenge import (
    Challenge,
    ChallengeDifficulty,
    ChallengeType,
    InstanceMode,
    WriteupVisibility,
    ChallengeFile,
    ChallengeHint,
    ChallengeWriteup,
)
from app.models.event import Event, EventStatus, event_challenges
from app.models.event_registration import EventRegistration, RegistrationType
from app.models.submission import Submission
from app.models.solve import Solve
from app.models.hint_usage import HintUsage
from app.models.activity import UserActivity, ActivityType
from app.models.badge import Badge, UserBadge, CriteriaType
from app.models.discussion import Discussion, DiscussionComment
from app.models.notification import Notification, NotificationType
from app.models.security_event import (
    SecurityEvent,
    SecurityEventReview,
    SecurityEventType,
    SecurityEventSeverity,
    SecurityEventStatus,
)

__all__ = [
    "Base",
    "TimeStampedModel",
    "User",
    "UserRole",
    "Team",
    "TeamMember",
    "team_members",
    "Category",
    "Challenge",
    "ChallengeDifficulty",
    "ChallengeType",
    "InstanceMode",
    "WriteupVisibility",
    "ChallengeFile",
    "ChallengeHint",
    "ChallengeWriteup",
    "Event",
    "EventStatus",
    "event_challenges",
    "EventRegistration",
    "RegistrationType",
    "Submission",
    "Solve",
    "HintUsage",
    "UserActivity",
    "ActivityType",
    "Badge",
    "UserBadge",
    "CriteriaType",
    "Discussion",
    "DiscussionComment",
    "Notification",
    "NotificationType",
    "SecurityEvent",
    "SecurityEventReview",
    "SecurityEventType",
    "SecurityEventSeverity",
    "SecurityEventStatus",
    "UserWriteup",
    "WriteupUpvote",
    "UserFollow",
    "GitHubIntegration",
    "GitHubSubmissionSync",
]

from app.models.solution import UserWriteup, WriteupUpvote
from app.models.follow import UserFollow
from app.models.github_integration import GitHubIntegration, GitHubSubmissionSync
