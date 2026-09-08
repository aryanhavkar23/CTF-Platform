import enum
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Uuid
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import utc_now


class ActivityType(str, enum.Enum):
    CHALLENGE_SOLVED = "challenge_solved"
    HINT_USED = "hint_used"
    EVENT_REGISTERED = "event_registered"
    TEAM_CREATED = "team_created"
    TEAM_JOINED = "team_joined"
    TEAM_LEFT = "team_left"


class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False, index=True)
    reference_id = Column(Uuid, nullable=True, index=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationship
    user = relationship("User", back_populates="activities")

    def __repr__(self) -> str:
        return f"<UserActivity user_id={self.user_id} type={self.activity_type!r} created_at={self.created_at}>"
