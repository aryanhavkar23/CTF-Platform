import uuid
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Uuid, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.base import utc_now


class Solve(Base):
    """Atomic ledger of verified challenge solves per user.
    
    The composite unique constraint ensures points can only ever be awarded once per challenge,
    even under concurrent race condition attempts.
    """
    __tablename__ = "solves"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_id = Column(Uuid, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_id = Column(Uuid, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    points_awarded = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "challenge_id", name="uq_user_challenge_solve"),
    )

    # Relationships
    user = relationship("User")
    challenge = relationship("Challenge")
    submission = relationship("Submission")

    def __repr__(self) -> str:
        return f"<Solve user_id={self.user_id} challenge_id={self.challenge_id} points={self.points_awarded}>"
