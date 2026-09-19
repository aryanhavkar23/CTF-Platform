import enum
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Uuid
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import utc_now


class SecurityEventType(str, enum.Enum):
    SUBMISSION_RATE_EXCEEDED = "submission_rate_exceeded"
    EXCESSIVE_FAILED_SUBMISSIONS = "excessive_failed_submissions"
    RAPID_MULTI_CHALLENGE_SOLVING = "rapid_multi_challenge_solving"
    REPEATED_CHALLENGE_ATTEMPTS = "repeated_challenge_attempts"
    CHALLENGE_ACCESS_VIOLATION = "challenge_access_violation"
    SUSPICIOUS_EVENT_ACTIVITY = "suspicious_event_activity"


class SecurityEventSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventStatus(str, enum.Enum):
    OPEN = "open"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    ACTIONED = "actioned"


class SecurityEvent(Base):
    """Immutable log of security and anti-cheat observations requiring review."""
    __tablename__ = "security_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id = Column(Uuid, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    event_id = Column(Uuid, ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)
    challenge_id = Column(Uuid, ForeignKey("challenges.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    description = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True, index=True)
    status = Column(String(20), default=SecurityEventStatus.OPEN.value, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    team = relationship("Team", foreign_keys=[team_id])
    event = relationship("Event", foreign_keys=[event_id])
    challenge = relationship("Challenge", foreign_keys=[challenge_id])
    reviews = relationship(
        "SecurityEventReview",
        back_populates="security_event",
        cascade="all, delete-orphan",
        order_by="desc(SecurityEventReview.created_at)"
    )

    def __repr__(self) -> str:
        return f"<SecurityEvent id={self.id} type={self.event_type!r} severity={self.severity!r} status={self.status!r}>"


class SecurityEventReview(Base):
    """Audit trail of administrative reviews and status transitions for security events."""
    __tablename__ = "security_event_reviews"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    security_event_id = Column(Uuid, ForeignKey("security_events.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    previous_status = Column(String(20), nullable=False)
    new_status = Column(String(20), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    security_event = relationship("SecurityEvent", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    def __repr__(self) -> str:
        return f"<SecurityEventReview event={self.security_event_id} from={self.previous_status!r} to={self.new_status!r}>"
