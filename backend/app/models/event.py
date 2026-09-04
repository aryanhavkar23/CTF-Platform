from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Table, Integer, Uuid, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import TimeStampedModel, utc_now


event_challenges = Table(
    "event_challenges",
    Base.metadata,
    Column("event_id", Uuid, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("challenge_id", Uuid, ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True),
    Column("points_override", Integer, nullable=True),
    Column("added_at", DateTime(timezone=True), default=utc_now, nullable=False),
)


class Event(TimeStampedModel):
    __tablename__ = "events"

    name = Column(String(150), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    is_scoreboard_frozen = Column(Boolean, default=False, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)

    # Constraints
    __table_args__ = (
        CheckConstraint("end_time > start_time", name="check_event_time_order"),
    )

    # Relationships
    challenges = relationship("Challenge", secondary=event_challenges, back_populates="events")
    submissions = relationship("Submission", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Event name={self.name!r} published={self.is_published}>"
