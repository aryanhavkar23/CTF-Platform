import uuid
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Uuid, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import utc_now


class HintUsage(Base):
    """Tracks which hints an authenticated student has unlocked.
    
    The composite unique constraint ensures a user can never use or be deducted
    points for the same hint more than once, even under concurrent requests.
    """
    __tablename__ = "hint_usage"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hint_id = Column(Uuid, ForeignKey("challenge_hints.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_id = Column(Uuid, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    points_deducted = Column(Integer, default=0, nullable=False)
    used_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "hint_id", name="uq_user_hint_usage"),
        Index("ix_hint_usage_user_challenge", "user_id", "challenge_id"),
    )

    # Relationships
    user = relationship("User")
    hint = relationship("ChallengeHint")
    challenge = relationship("Challenge")

    def __repr__(self) -> str:
        return f"<HintUsage user={self.user_id} hint={self.hint_id} deduction={self.points_deducted}>"
