import enum
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Table,
    Integer,
    Uuid,
    CheckConstraint,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimeStampedModel, utc_now


class EventStatus(str, enum.Enum):
    DRAFT = "draft"
    UPCOMING = "upcoming"
    LIVE = "live"
    ENDED = "ended"
    CANCELLED = "cancelled"


event_challenges = Table(
    "event_challenges",
    Base.metadata,
    Column("event_id", Uuid, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("challenge_id", Uuid, ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True),
    Column("points_override", Integer, nullable=True),
    Column("display_order", Integer, default=1, nullable=False),
    Column("is_active", Boolean, default=True, nullable=False),
    Column("added_at", DateTime(timezone=True), default=utc_now, nullable=False),
)


class Event(TimeStampedModel):
    __tablename__ = "events"

    name = Column(String(150), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(150), unique=True, index=True, nullable=False)

    start_at = Column(DateTime(timezone=True), nullable=False, index=True)
    end_at = Column(DateTime(timezone=True), nullable=False, index=True)
    registration_start_at = Column(DateTime(timezone=True), nullable=True)
    registration_end_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        SQLEnum(EventStatus, native_enum=False, length=20),
        default=EventStatus.UPCOMING,
        nullable=False,
        index=True
    )
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    is_scoreboard_frozen = Column(Boolean, default=False, server_default="false", nullable=False)
    scoreboard_frozen_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Backwards-compatibility columns for Phase 1 tests
    start_time = Column(DateTime(timezone=True), nullable=True, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True, index=True)
    is_published = Column(Boolean, default=False, nullable=True)

    # Constraints
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="check_event_time_order"),
    )

    def __init__(self, **kwargs):
        # Sync start_time / end_time with start_at / end_at
        if "start_time" in kwargs and "start_at" not in kwargs:
            kwargs["start_at"] = kwargs["start_time"]
        if "end_time" in kwargs and "end_at" not in kwargs:
            kwargs["end_at"] = kwargs["end_time"]
        if "start_at" in kwargs and "start_time" not in kwargs:
            kwargs["start_time"] = kwargs["start_at"]
        if "end_at" in kwargs and "end_time" not in kwargs:
            kwargs["end_time"] = kwargs["end_at"]

        # Default slug from name if not provided
        if "name" in kwargs and "slug" not in kwargs:
            import re
            cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", kwargs["name"]).strip().lower()
            kwargs["slug"] = re.sub(r"[\s-]+", "-", cleaned) or "event"

        super().__init__(**kwargs)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    challenges = relationship("Challenge", secondary=event_challenges, back_populates="events")
    submissions = relationship("Submission", back_populates="event", cascade="all, delete-orphan")
    registrations = relationship("EventRegistration", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Event name={self.name!r} status={self.status.value!r}>"
