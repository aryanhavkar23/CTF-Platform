import enum
import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Index, JSON, Uuid
from sqlalchemy.orm import relationship

from app.models.base import TimeStampedModel, utc_now


class NotificationType(str, enum.Enum):
    CHALLENGE_SOLVED = "challenge_solved"
    CHALLENGE_POINTS_AWARDED = "challenge_points_awarded"
    BADGE_AWARDED = "badge_awarded"
    TEAM_JOINED = "team_joined"
    TEAM_MEMBER_ADDED = "team_member_added"
    TEAM_MEMBER_REMOVED = "team_member_removed"
    TEAM_OWNER_TRANSFERRED = "team_owner_transferred"
    TEAM_INVITE_REQUEST = "team_invite_request"
    TEAM_INVITE_ACCEPTED = "team_invite_accepted"
    TEAM_INVITE_DECLINED = "team_invite_declined"
    EVENT_REGISTERED = "event_registered"
    EVENT_STARTED = "event_started"
    EVENT_ENDED = "event_ended"
    EVENT_SCOREBOARD_FROZEN = "event_scoreboard_frozen"
    DISCUSSION_REPLY = "discussion_reply"


class Notification(TimeStampedModel):
    """Represents an in-app notification delivered to a user."""
    __tablename__ = "notifications"

    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    type = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True)
    event_key = Column(String(255), nullable=True, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_is_read", "user_id", "is_read"),
        Index("ix_notifications_user_created_at", "user_id", "created_at"),
        Index("ix_notifications_user_event_key", "user_id", "event_key"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} type={self.type} is_read={self.is_read}>"
