import enum
import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Uuid,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import utc_now


class RegistrationType(str, enum.Enum):
    INDIVIDUAL = "individual"
    TEAM = "team"


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    event_id = Column(Uuid, ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    team_id = Column(Uuid, ForeignKey("teams.id", ondelete="CASCADE"), nullable=True, index=True)
    registration_type = Column(String(20), nullable=False)  # "individual" or "team"
    registered_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)

    __table_args__ = (
        CheckConstraint(
            "(registration_type = 'individual' AND user_id IS NOT NULL AND team_id IS NULL) OR "
            "(registration_type = 'team' AND team_id IS NOT NULL AND user_id IS NULL)",
            name="chk_event_reg_participant_type"
        ),
        UniqueConstraint("event_id", "user_id", name="uq_event_user_reg"),
        UniqueConstraint("event_id", "team_id", name="uq_event_team_reg"),
    )

    # Relationships
    event = relationship("Event", back_populates="registrations")
    user = relationship("User")
    team = relationship("Team")

    def __repr__(self) -> str:
        participant = f"user={self.user_id}" if self.user_id else f"team={self.team_id}"
        return f"<EventRegistration event={self.event_id} {participant} type={self.registration_type}>"
